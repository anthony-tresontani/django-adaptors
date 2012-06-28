"""
Define the csv model base classe
"""
import copy

import csv
from django.db.models.base import Model
from adaptor.fields import Field, IgnoredField, ComposedKeyField, XMLRootField
from adaptor.exceptions import ForeignKeyFieldError, FieldValueMissing


class ImproperlyConfigured(Exception):
    """
    Raised if a missing config value is detected
    """


class CsvException(Exception):
    """
    Raised if a problem in the file is detected
    """


class CsvDataException(CsvException):
    """
    Raised if a data does not match the expectations
    """
    def __init__(self, line, error=None, field_error=None):
        self.line = line + 1
        self.error = error
        self.field_error = field_error
        err_msg = self.error if self.error else self.field_error
        super(CsvDataException, self).__init__(u"Line %d: %s" % (self.line, err_msg))


class CsvFieldDataException(CsvDataException):
    def __init__(self, line, field_error, model, value):
        self.model = model
        self.value = value
        super(CsvFieldDataException, self).__init__(line, field_error=field_error)


class SkipRow(Exception):
    pass


class BaseModel(object):
    def __init__(self, data, delimiter=None):
        self.cls = self.__class__
        self.attrs = self.get_fields()
        self.errors = []
        self.dont_raise_exception = hasattr(self.cls, "Meta") and hasattr(self.cls.Meta, "raise_exception") and not self.cls.Meta.raise_exception

    def is_valid(self):
        return len(self.errors) == 0

    @classmethod
    def get_fields(cls):
        all_cls_dict = {}
        all_cls_dict.update(cls.__dict__)
        for klass in cls.__bases__:
            all_cls_dict.update(klass.__dict__)

        # Add a copy the attribute to not have interference between differente instance
        # of a same class
        attributes = [(attr, copy.copy(all_cls_dict[attr])) for attr in all_cls_dict
                                                 if isinstance(all_cls_dict[attr],
                                                                Field)]
        for fieldname, field in attributes:
            field.fieldname = fieldname

        sorted_field = sorted(attributes, key=lambda attrs: attrs[1].position)
        return sorted_field

    @classmethod
    def get_data_fields(cls):
       return [fieldname for (fieldname, field) in cls.get_fields() if fieldname not in getattr(cls, "_exclude_data_fields", [])]

    def as_dict(self):
       return dict((field, getattr(self, field)) for field in self.get_data_fields())

    def get_value(self, attr_name, field, value):
        self.__dict__[attr_name] = field.get_prep_value(value)
        self.field_matching_name = field.__dict__.get("match", attr_name)
        return field.get_prep_value(value)

    def update_object(self, dict_values, object, update_dict):
        new_dict_values = {}
        if 'update' in update_dict:
            # Update the object for the value un update_dict['update']
            # only
            for field_name in update_dict['update']:
                new_dict_values[field_name] = dict_values[field_name]
        else:
            new_dict_values = dict_values
        for field_name in new_dict_values:
            setattr(object, field_name, new_dict_values[field_name])
        object.save()

    def base_create_model(self, model, **dict_values):
        object = None
        if self.cls.has_update_method():
            keys = None
            update_dict = self.cls.Meta.update
            try:
                keys = update_dict['keys']
            except KeyError:
                raise ImproperlyConfigured("The update dict should contains a keys value")
            filter_values = {}
            for key in keys:
                filter_values.update({key: dict_values[key]})
            object = None
            try:
                object = model.objects.get(**filter_values)
            except model.DoesNotExist:
                object = model.objects.create(**dict_values)
            except model.MultipleObjectsReturned:
                raise ImproperlyConfigured(
                    "Multiple values returned for the update key %s.\
                                        Keys provide are not unique" % filter_values)
            else:
                self.update_object(dict_values, object, update_dict)
        else:
            object = model.objects.create(**dict_values)
        self.object = object

    def get_object(self):
        if self.cls.is_db_model():
            return self.object
        return None

    def create_model_instance(self, values):
        model = self.cls.Meta.dbModel
        if self.multiple_creation_field:
            if self.multiple_creation_field:
                multiple_values = values.pop(self.multiple_creation_field)
                for value in multiple_values:
                    dict_values = values.copy()
                    dict_values[self.multiple_creation_field] = value
                    self.base_create_model(model, **dict_values)

        else:
            self.base_create_model(model, **values)

    def set_values(self, values_dict, fields_name, values):
        if isinstance(fields_name, list):
            for field_name in fields_name:
                values_dict[field_name] = values
        else:
            values_dict[fields_name] = values

    def construct_obj_from_model(self, object):
        for field_name, field in self.get_fields():
            setattr(self,
                    field_name,
                    getattr(object,
                            # If match attribute is defined, use the match name,
                            # else use the field name
                            field.__dict__.get("match", field_name), None))
        return self

    def export(self):
        line = u""
        for field_name, field in self.get_fields():
            line += unicode(getattr(self, field_name))
            line += self.delimiter
        return line.rstrip(self.delimiter) # remove the extra delimiter

    @classmethod
    def is_db_model(cls):
        return hasattr(cls, "Meta") and hasattr(cls.Meta, "dbModel") and cls.Meta.dbModel

    @classmethod
    def has_class_delimiter(cls):
        return hasattr(cls, "Meta") and hasattr(cls.Meta, "delimiter")

    @classmethod
    def has_header(cls):
        return hasattr(cls, "Meta") and hasattr(cls.Meta, "has_header") and cls.Meta.has_header

    @classmethod
    def has_update_method(cls):
        has_update = hasattr(cls, "Meta") and hasattr(cls.Meta, "update")
        if has_update and not cls.is_db_model():
            raise ImproperlyConfigured("You should define a model when using the update option")
        return has_update

    @classmethod
    def silent_failure(cls):
        if not hasattr(cls, "Meta") or not hasattr(cls.Meta, "silent_failure"):
            return False
        return cls.Meta.silent_failure

    @classmethod
    def import_data(cls, data, extra_fields=[]):
        importer = cls.get_importer(extra_fields)
        return importer.import_data(data)

    @classmethod
    def import_from_filename(cls, filename, extra_fields=[]):
        importer = cls.get_importer(extra_fields=extra_fields)
        return importer.import_from_filename(filename)

    @classmethod
    def import_from_file(cls, file, extra_fields=[]):
        importer = cls.get_importer(extra_fields=extra_fields)
        return importer.import_from_file(file)


class CsvModel(BaseModel):

    def __init__(self, data, delimiter=None):
        super(CsvModel, self).__init__(data)
        self.delimiter = None
        if delimiter:
            self.delimiter = delimiter
        elif self.has_class_delimiter():
            self.   delimiter = self.cls.Meta.delimiter
        if not isinstance(data, Model):
            self.construct_obj_from_data(data)
        else:
            self.construct_obj_from_model(data)


    def validate(self):
        if len(self.attrs) == 0:
            raise ImproperlyConfigured("No field defined. Should have at least one field in the model.")
        if not self.cls.has_class_delimiter() and not getattr(self, "delimiter", False) and len(self.attrs) > 1:
            raise ImproperlyConfigured(
            "More than a single field and no delimiter defined. You should define a delimiter.")

    @classmethod
    def get_importer(cls, extra_fields=[]):
        return CsvImporter(csvModel=cls, extra_fields=extra_fields)

    def construct_obj_from_data(self, data):
        self.validate()
        values = {}
        silent_failure = self.cls.silent_failure()
        self.multiple_creation_field = None
        composed_fields = []
        index_offset = 0
        data_offset = 0
        for position, (attr_name, field) in enumerate(self.attrs):
            field.position = position
            if isinstance(field, ComposedKeyField):
                composed_fields.append(field)
                index_offset += 1
                continue
            if self.cls.has_class_delimiter() or self.delimiter:
                value = data.pop(position - index_offset - data_offset)
                data_offset += 1
            else:
                value = data.pop(0)
            try:
                if isinstance(field, IgnoredField):
                    continue
                if hasattr(field, 'has_multiple') and field.has_multiple:
                    remaining_data = [value] + data[:] # value should be re-added
                    # as it has been pop before
                    multiple_values = []
                    for data in remaining_data:
                        multiple_values.append(self.get_value(attr_name, field, data))
                    self.set_values(values, self.field_matching_name, multiple_values)
                    self.multiple_creation_field = self.field_matching_name
                else:
                    value = self.get_value(attr_name, field, value)
                    self.set_values(values, self.field_matching_name, value)
            except ValueError, e:
                if silent_failure:
                   raise SkipRow()
                else:
                    raise e
        if self.cls.is_db_model():
            for field in composed_fields:
                keys = {}
                for key in field.keys:
                    keys[key] = values.pop(key)
                values[self.field_matching_name] = self.get_value(attr_name, field, keys)
            self.create_model_instance(values)


class CsvDbModel(CsvModel):
    def validate(self):
        if not self.cls.is_db_model():
            raise ImproperlyConfigured("dbModel attribute is missing \
                                        or wrongly configured in the \
                                        CsvDbModel class.")

    @classmethod
    def get_fields(cls):
        cls_attrs = super(CsvDbModel, cls).get_fields()
        if len(cls_attrs) != 0:
            raise ImproperlyConfigured("A Db model should not have any csv field defined.")
        attrs = []
        if cls.is_db_model():
            model = cls.Meta.dbModel
            for field in model._meta.fields:
                attrs.append((field.name, field))
        excluded_fields = cls.get_exclusion_fields()
        attrs_filtered = [attr for attr in attrs if attr[0] not in excluded_fields]
        return attrs_filtered

    @classmethod
    def get_exclusion_fields(cls):
        list_exclusion = []
        if hasattr(cls, "Meta") and hasattr(cls.Meta, "exclude"):
            list_exclusion.append(*cls.Meta.exclude)
        if 'id' not in list_exclusion:
            list_exclusion.append('id')
        return list_exclusion


class XMLModel(BaseModel):
    _exclude_data_fields = ['root']

    def __init__(self, data, element=None):
        super(XMLModel, self).__init__(data)
        self._base_root = element
        self.construct_obj_from_data(data)

    def validate(self):pass

    @classmethod
    def get_root_field(cls):
        for field_name, field in cls.get_fields():
            if type(field) == XMLRootField:
                return field_name, field
        return None

    def set_field_value(self, field_name, field, data):
        try:
            self.__dict__[field_name] = field.get_prep_value(data, instance=self)
        except IndexError:
            raise FieldValueMissing(field_name)

    def construct_obj_from_data(self, data):
        for field_name, field in self.attrs:
            field.set_root(self._base_root)
            try:
                self.set_field_value(field_name, field, data)
            except Exception, e:
                if self.dont_raise_exception:
                   self.errors.append((field_name,e.message))
                   continue
                else:
                   raise

    @classmethod
    def get_importer(cls, *args):
        return XMLImporter(model=cls)


class XMLImporter(object):
    def __init__(self, model):
        self.model = model

    def import_data(self, data):
        root_name, root_field = self.model.get_root_field()
        objects = []
        for element in root_field.get_root(data):
            object = self.model(data, element)
            objects.append(object)
        return objects


class LinearLayout(object):
    def process_line(self, lines, line, model, delimiter):
        fields = model.get_fields()
        multiple_index = 0
        for index, (fieldname, field) in enumerate(fields):
            if hasattr(field, "has_multiple") and field.has_multiple:
               multiple_index = index 
               multiple_index_fieldname = fieldname
               break
        if multiple_index:
            if not line[multiple_index:]:
                raise ValueError("No value found for column %s" % multiple_index_fieldname) 
            for index, val in enumerate(line[multiple_index:]):
                line_ = line[0:multiple_index] + [line[multiple_index + index]]
                value = model(data=line_, delimiter=delimiter)
                lines.append(value)
        else:
            # Need to keep that to preserve the side effect on line
            value = model(data=line, delimiter=delimiter)
            lines.append(value)
        return value


class TabularLayout(object):
    def __init__(self):
        self.line_no = 0
        self.column_no = 1
        self.headers = None

    def process_line(self, lines, line, model, delimiter):
        value = None
        if self.line_no == 0:
            self.headers = line
            self.line_no += 1
        else:
            for data in line[1:]:
                inline_data = [line[0], self.headers[self.column_no], data]
                value = model(data=inline_data, delimiter=delimiter)
                lines.append(value)
                self.column_no += 1
            self.column_no = 1
        return value


class GroupedCsvModel(CsvModel):
    @classmethod
    def get_importer(cls, extra_fields=[]):
        return GroupedCsvImporter(csvModel=cls, extra_fields=extra_fields)

    @classmethod
    def has_csv_models(cls):
        return hasattr(cls, "Meta") and hasattr(cls.Meta, "has_header") and cls.Meta.has_header


    def validate(self):
        if len(self.attrs) != 0:
            raise ImproperlyConfigured("You cannot define fields in \
                                        a grouped csv model.")
        if not hasattr(self.cls, "csv_models") or\
           not isinstance(self.cls.csv_models, list) or\
           len(self.cls.csv_models) == 0:
            raise ImproperlyConfigured("Group csv models should define a\
                                        non empty csv_models list attribute.")


class CsvImporter(object):
    def __init__(self, csvModel, extra_fields=[], layout=None):
        self.csvModel = csvModel
        self.extra_fields = extra_fields
        self.dialect = None
        self.delimiter = None
        if not layout:
            if hasattr(self.csvModel, 'Meta') and hasattr(self.csvModel.Meta, 'layout'):
                self.layout = self.csvModel.Meta.layout()
            else:
                self.layout = LinearLayout()


    def process_extra_fields(self, data, line):
        data_length = len(line)
        if self.extra_fields:
            extra_field_index = 0
            for value in self.extra_fields:
                if isinstance(value, str):
                    line.append(value)
                elif isinstance(value, dict):
                    position = value.get('position', len(data) + extra_field_index)
                    if not 'value' in value:
                        raise CsvException("If a positional extra argument is \
                                            defined, a value key should \
                                            be present.")
                    line.insert(position, value['value'])
                else:
                    raise ImproperlyConfigured("Extra field should be a string or a list")

    def import_data(self, data):
        lines = []
        self.get_class_delimiter()
        line_number = 0
        for line in csv.reader(data, delimiter=self.delimiter):
            self.process_line(data, line, lines, line_number, self.csvModel)
            line_number += 1
        return lines


    def process_line(self, data, line, lines, line_number, model):
        self.process_extra_fields(data, line)
        value = None
        try:
            value = self.layout.process_line(lines, line, model, delimiter=self.delimiter)
        except SkipRow:
            pass
        except ForeignKeyFieldError, e:
            raise CsvFieldDataException(line_number, field_error=e.message, model=e.model, value=e.value)
        except ValueError, e:
            if line_number == 0 and self.csvModel.has_header():
                pass
            else:
                raise CsvDataException(line_number, field_error=e.message)
        except IndexError, e:
            raise CsvDataException(line_number, error="Number of fields invalid")
        return value


    def get_class_delimiter(self):
        if not self.delimiter and hasattr(self.csvModel, 'Meta') and hasattr(self.csvModel.Meta, 'delimiter'):
            self.delimiter = self.csvModel.Meta.delimiter

    def import_from_filename(self, filename):
        csv_file = open(filename)
        return self.import_from_file(csv_file)

    def import_from_file(self, csv_file):
        self.get_class_delimiter()
        if not self.delimiter:
            dialect = csv.Sniffer().sniff(csv_file.read(1024))
            self.delimiter = dialect.delimiter
        csv_file.seek(0)
        return self.import_data(csv_file)


    def __getitem__(self, item):
        return self.lines[item]

    def __iter__(self):
        return self.lines.__iter__()


class GroupedCsvImporter(CsvImporter):
    def process_line(self, data, line, lines, line_number, model):
        previous_value = None
        for model in self.csvModel.csv_models:
            if isinstance(model, dict):
                if "use" in model:
                    line.insert(0, previous_value.get_object().id)
                previous_value = super(GroupedCsvImporter, self).process_line(data, line, lines, line_number,
                                                                              model['model'])
            else:
                super(GroupedCsvImporter, self).process_line(data, line, lines, line_number, model)

