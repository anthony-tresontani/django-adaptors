import csv

from django.db.models.fields import Field as DjangoField
from fields import Field
from django.core.exceptions import ValidationError

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

    def __init__(self,data,delimiter=None):
        self.delimiter = delimiter
        self.cls = self.__class__
        self.attrs = self.get_fields()
        self.validate()
        values = {}
        silent_failure = self.cls.silent_failure()
        load_failed = False
        for (attr_name,field),position in zip(self.attrs,range(len(self.attrs))):
            field.position = position
            if self.cls.has_class_delimiter() or delimiter:
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
        if self.cls.is_db_model():
            print "DB model"
        if self.cls.is_db_model() and not load_failed:
            print "values: %s" % values
            model = self.cls.Meta.dbModel
            model.objects.create(**values)

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
        print "Attributes %s" % attrs_filtered
        return attrs_filtered
    
    @classmethod
    def get_exclusion_fields(cls):
        list_exclusion = []
        if hasattr(cls,"Meta") and hasattr(cls.Meta,"exclude"):
            list_exclusion.append(*cls.Meta.exclude)
        if 'id' not in list_exclusion:
            list_exclusion.append('id')
        return list_exclusion
            

class CsvImporter(object):

    def __init__(self,csvModel,extra_fields=[]):
        self.csvModel = csvModel
        self.extra_fields = extra_fields
        self.dialect = None
        self.delimiter = None
        

    def process_extra_fields(self, data, line):
        data_length = len(line)
        if self.extra_fields:
            extra_field_index = 0
            for value in self.extra_fields:
                if isinstance(value, str):
                    line.append(value)
                if isinstance(value, dict):
                    position = value.get('position', len(data) + extra_field_index)
                    if not 'value' in value:
                        raise ValueError("If a positional extra argument is defined, a value key should be present.")
                    line.insert(position, value['value'])
                    print "Extra: %s" % data

    def import_data(self,data):
        lines = []
        has_header_anymore = self.csvModel.has_header()
        self.get_class_delimiter()
        for line in csv.reader(data,delimiter = self.delimiter):
            self.process_extra_fields(data, line)
            try :
                lines.append(self.csvModel(data=line,delimiter=self.delimiter))
            except ValueError, e:
                if has_header_anymore:
                    pass
                else:
                    raise e
            if has_header_anymore:
                has_header_anymore = False
        return lines
        
    def get_class_delimiter(self):
        if not self.delimiter and hasattr(self.csvModel,'Meta') and hasattr(self.csvModel.Meta,'delimiter'):
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


