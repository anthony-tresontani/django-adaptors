import csv

from django.db.models.fields import Field as DjangoField
from fields import Field

class ImproperlyConfigured(Exception):
    pass

class CsvModel(object):

    def get_fields(self):
        all_cls_dict = {}
        all_cls_dict.update(self.cls.__dict__)
        for klass in self.cls.__bases__:
            all_cls_dict.update(klass.__dict__)
        attributes = [(attr, all_cls_dict[attr] ) for attr in all_cls_dict if isinstance(all_cls_dict[attr], Field)]
        sorted_field = sorted(attributes,key=lambda attrs: attrs[1].position)
        return sorted_field

    def __init__(self,data):
        self.cls = self.__class__
        self.attrs = self.get_fields()
        self.validate()
        values = {}
        silent_failure = self.cls.silent_failure()
        load_failed = False
#        import pdb;pdb.set_trace()
        for (attr_name,field),position in zip(self.attrs,range(len(self.attrs))):
            field.position = position
            if self.cls.has_delimiter():
                value = data[position]
            else:
                value = data[0]
            try:
                self.__dict__[attr_name] = field.get_prep_value(value)
                field_matching_name = field.__dict__.get("match",attr_name)
                values[field_matching_name] = field.get_prep_value(value)
            except ValueError,e :
                if silent_failure:
                    load_failed = True
                    break
                else:
                    print e
                    raise e
        if self.cls.is_db_model() and not load_failed:
            print "values: %s" % values
            model = self.cls.Meta.dbModel
            model.objects.create(**values)

    def validate(self):
        if len(self.attrs)==0:
            raise ImproperlyConfigured("No field defined. Should have at least one field in the model.")
        if not self.cls.has_delimiter() and len(self.attrs)>1:
            raise ImproperlyConfigured("More than a single field and no delimiter defined. You should define a delimiter.")
        

    @classmethod
    def is_db_model(cls):
        return hasattr(cls,"Meta") and hasattr(cls.Meta,"dbModel") and cls.Meta.dbModel

    @classmethod
    def has_delimiter(cls):
        return hasattr(cls,"Meta") and hasattr(cls.Meta,"delimiter")
    
    @classmethod
    def has_header(cls):
        return hasattr(cls,"Meta") and hasattr(cls.Meta,"has_header") and cls.Meta.has_header
    
    @classmethod
    def silent_failure(cls):
        if not hasattr(cls,"Meta") or not hasattr(cls.Meta,"silent_failure"):
            return False
        return cls.Meta.silent_failure

    @classmethod
    def import_data(cls,data):
        return CsvImporter(data=data,csvModel=cls)

class CsvDbModel(CsvModel):
        
    def validate(self):
        if not self.cls.is_db_model():
            raise ImproperlyConfigured("dbModel attribute is missing or wrongly configured in the CsvDbModel class.")
        
    def get_fields(self):
        cls = self.__class__
        attrs = []
        if cls.is_db_model():
            model = cls.Meta.dbModel
            for field in model._meta.fields:
                attrs.append((field.name,field))
        excluded_fields = cls.get_exclusion_fields()
        attrs_filtered = [attr for attr in attrs if attr[0] not in excluded_fields]
        print "Attributes %s" % attrs_filtered
        return attrs_filtered
    
    @classmethod
    def get_exclusion_fields(cls):
        list_exclusion = []
        if hasattr(cls,"Meta") and hasattr(cls.Meta,"delimiter"):
            list_exclusion.append(*cls.Meta.exclude)
        if 'id' not in list_exclusion:
            list_exclusion.append('id')
        return list_exclusion
            

class CsvImporter(object):

    def __init__(self,data,csvModel):
        self.data = data
        self.csvModel = csvModel
        self.lines = []
        if hasattr(csvModel,'Meta') and hasattr(csvModel.Meta,'delimiter'):
            delimiter = csvModel.Meta.delimiter
        else:
            delimiter=","
        has_header_anymore = csvModel.has_header()
        for line in csv.reader(self.data,delimiter=delimiter):
            if has_header_anymore:
                has_header_anymore = False
                continue
            self.lines.append(csvModel(data=line))

    def __getitem__(self, item):
        return self.lines[item]

    def __iter__(self):
        return self.lines.__iter__()


