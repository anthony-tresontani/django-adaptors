import csv
from django.db.models.fields import Field as DjangoField
from fields import Field, ForeignKeyFieldError, IgnoredField, ComposedKeyField
from django.core.exceptions import ValidationError

class ImproperlyConfigured(Exception):
    pass

class CsvException(Exception):
    pass
        
class CsvDataException(CsvException):
    def __init__(self, line, error=None ,field_error=None):
        self.line = line + 1
        self.error = error
        self.field_error = field_error
        if self.error:
            Exception.__init__(self,u"Line %d: %s" % (self.line ,self.error))
        elif self.field_error:
            Exception.__init__(self,u"Line %d: %s" % (self.line ,self.field_error))
            
class CsvFieldDataException(CsvDataException):
    def __init__(self, line, field_error, model, value):
        self.model = model
        self.value = value
        CsvDataException.__init__(self,line, field_error=field_error)
        
class SkipRow(Exception): pass
            
        
class CsvModel(object):

    def get_fields(self):
        all_cls_dict = {}
        all_cls_dict.update(self.cls.__dict__)
        for klass in self.cls.__bases__:
            all_cls_dict.update(klass.__dict__)
        attributes = [(attr, all_cls_dict[attr] ) for attr in all_cls_dict if isinstance(all_cls_dict[attr], Field)]
        sorted_field = sorted(attributes,key=lambda attrs: attrs[1].position)
        return sorted_field


    def get_value(self, attr_name, field, value):
        self.__dict__[attr_name] = field.get_prep_value(value)
        self.field_matching_name = field.__dict__.get("match", attr_name)
#        values[field_matching_name] = field.get_prep_value(value)
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
            attr = setattr(object, field_name, new_dict_values[field_name])
        object.save()

    def base_create_model(self, model, **dict_values):
        if self.cls.has_update_method():
            keys = None
            update_dict = self.cls.Meta.update
            try:
                keys = update_dict['keys']
            except KeyError:
                raise ImproperlyConfigured("The update dict should contains a keys value")
            filter_values = {}
            for key in keys:
                filter_values.update({key:dict_values[key]})
            object = None
            try:
                object = model.objects.get(**filter_values)
            except model.DoesNotExist:
                object = model.objects.create(**dict_values)
            except model.MultipleObjectsReturned:
                raise ImproperlyConfigured("Multiple values returned for the update key %s. Keys provide are not unique" % filter_values)
            else:
                self.update_object(dict_values, object, update_dict)
        else:
            model.objects.create(**dict_values)


    def create_model_instance(self, values):
        model = self.cls.Meta.dbModel
        if self.multiple_creation_field:
            if self.multiple_creation_field:
                multiple_values = values.pop(self.multiple_creation_field)
                for value in multiple_values:
                    dict_values = values.copy()
                    dict_values[self.multiple_creation_field] = value
                    self.base_create_model( model, **dict_values)
                    
        else:
            self.base_create_model( model, **values)

    def __init__(self,data,delimiter=None):
        self.delimiter = delimiter
        self.cls = self.__class__
        self.attrs = self.get_fields()
        self.validate()
        values = {}
        silent_failure = self.cls.silent_failure()
        load_failed = False
        self.multiple_creation_field = None
        composed_fields = []
        index_offset = 0
        for (attr_name,field),position in zip(self.attrs,range(len(self.attrs))):
            field.position = position
            if isinstance(field, ComposedKeyField):
                    composed_fields.append(field)
                    index_offset += 1
                    continue
            if self.cls.has_class_delimiter() or delimiter:
                value = data[position - index_offset]
            else:
                value = data[0]
            try:
                if isinstance(field, IgnoredField):
                    continue
                if hasattr(field,'has_multiple') and field.has_multiple:
                    remaining_data = data[position:]
                    multiple_values = []
                    for data in remaining_data:
                        multiple_values.append(self.get_value(attr_name, field, data))
                    values[self.field_matching_name] = multiple_values
                    self.multiple_creation_field = self.field_matching_name
                else:
                    values[self.field_matching_name] = self.get_value(attr_name, field, value)
            except ValueError,e :
                if silent_failure:
                    load_failed = True
                    break
                else:
                    raise e
        if self.cls.is_db_model() and not load_failed:
            for field in composed_fields:
                keys = {}
                for key in field.keys:
                    keys[key]=values.pop(key)
                values[self.field_matching_name] = self.get_value(attr_name, field, keys)
            self.create_model_instance(values)

    def validate(self):
        if len(self.attrs)==0:
            raise ImproperlyConfigured("No field defined. Should have at least one field in the model.")
        if not self.cls.has_class_delimiter() and not self.delimiter and len(self.attrs)>1:
            raise ImproperlyConfigured("More than a single field and no delimiter defined. You should define a delimiter.")
        

    @classmethod
    def is_db_model(cls):
        return hasattr(cls,"Meta") and hasattr(cls.Meta,"dbModel") and cls.Meta.dbModel

    @classmethod
    def has_class_delimiter(cls):
        return hasattr(cls,"Meta") and hasattr(cls.Meta,"delimiter")
    
    @classmethod
    def has_header(cls):
        return hasattr(cls,"Meta") and hasattr(cls.Meta,"has_header") and cls.Meta.has_header
    
    @classmethod
    def has_update_method(cls):
        has_update = hasattr(cls,"Meta") and hasattr(cls.Meta,"update")
        if has_update and not cls.is_db_model():
            raise ImproperlyConfigured("You should define a model when using the update option")
        return has_update
        
    @classmethod
    def silent_failure(cls):
        if not hasattr(cls,"Meta") or not hasattr(cls.Meta,"silent_failure"):
            return False
        return cls.Meta.silent_failure

    @classmethod
    def import_data(cls,data,extra_fields=[]):
        importer =  CsvImporter(csvModel=cls,extra_fields=extra_fields)
        return importer.import_data(data)
    
    @classmethod
    def import_from_filename(cls,filename,extra_fields=[]):
        importer =  CsvImporter(csvModel=cls,extra_fields=extra_fields)
        return importer.import_from_filename(filename)
    
    @classmethod
    def import_from_file(cls,file,extra_fields=[]):
        importer =  CsvImporter(csvModel=cls,extra_fields=extra_fields)
        return importer.import_from_file(file)
    


class CsvDbModel(CsvModel):
        
    def validate(self):
        if not self.cls.is_db_model():
            raise ImproperlyConfigured("dbModel attribute is missing or wrongly configured in the CsvDbModel class.")
        
    def get_fields(self):
        cls_attrs = super(CsvDbModel,self).get_fields()
        if len(cls_attrs) != 0:
            raise ImproperlyConfigured("A Db model should not have any csv field defined.")
        cls = self.__class__
        attrs = []
        if cls.is_db_model():
            model = cls.Meta.dbModel
            for field in model._meta.fields:
                attrs.append((field.name,field))
        excluded_fields = cls.get_exclusion_fields()
        attrs_filtered = [attr for attr in attrs if attr[0] not in excluded_fields]
        return attrs_filtered
    
    @classmethod
    def get_exclusion_fields(cls):
        list_exclusion = []
        if hasattr(cls,"Meta") and hasattr(cls.Meta,"exclude"):
            list_exclusion.append(*cls.Meta.exclude)
        if 'id' not in list_exclusion:
            list_exclusion.append('id')
        return list_exclusion
            
class LinearLayout(object):
    
    def process_line(self, lines, line, model,delimiter):
        lines.append(model(data=line,delimiter=delimiter))
        
class TabularLayout(object):
    
    def __init__(self):
        self.line_no = 0
        self.column_no = 1
        self.headers = None
    
    def process_line(self, lines, line, model,delimiter):
        if self.line_no == 0:
            self.headers = line
            self.line_no += 1
        else:
            for data in line[1:]:
                inline_data = [line[0],self.headers[self.column_no],data]
                lines.append(model(data=inline_data,delimiter=delimiter))
                self.column_no += 1
            self.column_no = 1
            
class CsvImporter(object):

    def __init__(self, csvModel, extra_fields=[], layout = None):
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
                        raise CsvException("If a positional extra argument is defined, a value key should be present.")
                    line.insert(position, value['value'])
                else:
                    raise ImproperlyConfigured("Extra field should be a string or a list")

    def import_data(self,data):
        lines = []
        self.get_class_delimiter()
        line_number = 0
        for line in csv.reader(data,delimiter = self.delimiter):
            self.process_line(data, line, lines, line_number)
            line_number += 1
        return lines
        
        
    def process_line(self, data, line, lines, line_number):
        self.process_extra_fields(data, line)
        try :
            self.layout.process_line(lines, line, self.csvModel, delimiter = self.delimiter)
        except SkipRow:
            pass
        except ForeignKeyFieldError, e:
            raise CsvFieldDataException(line_number, field_error =  e.message, model = e.model, value = e.value)
        except ValueError, e:
            if line_number == 0 and self.csvModel.has_header():
                pass
            else:
                raise CsvDataException(line_number, field_error =  e.message)
        except IndexError,e :
            raise CsvDataException(line_number, error = "Number of fields invalid")
        
        
        
    def get_class_delimiter(self):
        if not self.delimiter and hasattr(self.csvModel, 'Meta') and hasattr(self.csvModel.Meta, 'delimiter'):
            self.delimiter = self.csvModel.Meta.delimiter
            
    def import_from_filename(self,filename):
        csv_file = open(filename)
        return self.import_from_file(csv_file)
    
    def import_from_file(self,csv_file):
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


