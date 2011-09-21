import csv
from fields import Field

class ImproperlyConfigured(Exception):
    pass

class CsvModel(object):

    def get_fields(self, cls):
        all_cls_dict = {}
        all_cls_dict.update(cls.__dict__)
        for klass in cls.__bases__:
            all_cls_dict.update(klass.__dict__)
        attrs = [(attr, all_cls_dict[attr] ) for attr in all_cls_dict if isinstance(all_cls_dict[attr], Field)]
        return attrs

    def __init__(self,data):
        cls = self.__class__
        attrs = self.get_fields(cls)
        if len(attrs)==0:
            raise ImproperlyConfigured("No field defined. Should have at least one field in the model.")
        if not cls.has_delimiter() and len(attrs)>1:
            raise ImproperlyConfigured("More than a single field and no delimiter defined. You should define a delimiter.")
        sorted_field = sorted(attrs,key=lambda attrs: attrs[1].position)
        values = {}
        for (attr_name,field),position in zip(sorted_field,range(len(sorted_field))):
            field.position = position
            if cls.has_delimiter():
                value = data[position]
            else:
                value = data[0]
            self.__dict__[attr_name] = field.get_value(value)
            print field.__dict__
            field_matching_name = field.__dict__.get("match",attr_name)
            values[field_matching_name] = field.get_value(value)
        if cls.is_db_model():
            model = cls.Meta.dbModel
            model.objects.create(**values)

    @classmethod
    def is_db_model(cls):
        return hasattr(cls,"Meta") and hasattr(cls.Meta,"dbModel")

    @classmethod
    def has_delimiter(cls):
        return hasattr(cls,"Meta") and hasattr(cls.Meta,"delimiter")

    @classmethod
    def import_data(cls,data):
        return CsvImporter(data=data,csvModel=cls)

class CsvImporter(object):

    def __init__(self,data,csvModel):
        self.data = data
        self.csvModel = csvModel
        self.lines = []
        if hasattr(csvModel,'Meta') and hasattr(csvModel.Meta,'delimiter'):
            delimiter = csvModel.Meta.delimiter
        else:
            delimiter=","
        for line in csv.reader(self.data,delimiter=delimiter):
            self.lines.append(csvModel(data=line))

    def __getitem__(self, item):
        return self.lines[item]

    def __iter__(self):
        return self.lines.__iter__()


