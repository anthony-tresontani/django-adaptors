from django.db.models import Model as djangoModel
from django.core.exceptions import ObjectDoesNotExist

class FieldError(ValueError):
    pass

class Field(object):
    position =0

    def __init__(self,**kwargs):
        if 'row_num' in kwargs:
            self.position = kwargs.pop('row_num')
        else:
            self.position = Field.position
            Field.position += 1
        if 'match' in kwargs:
            self.match = kwargs.pop('match')
        if 'transform' in kwargs:
            self.transform = kwargs.pop('transform')
        if 'validator' in kwargs:
            self.validator = kwargs.pop('validator')
        if 'multiple' in kwargs:
            self.has_multiple = kwargs.pop('multiple')
        if len(kwargs)>0:
            raise ValueError("Arguments %s unexpected" % kwargs.keys())

    def get_prep_value(self,value):
        try:
            value = self.to_python(value)
            if hasattr(self,"transform"):
                value = self.transform(value)
            if hasattr(self,"validator"):
                validator = self.validator()
                if not validator.validate(value):
                    raise FieldError(validator.__class__.validation_message)
            return value
        except FieldError, e:
            raise e
        except ValueError:
            raise ValueError("Value \'%s\' in columns %d does not match the expected type %s" % (value,self.position+1,self.__class__.field_name))


class IntegerField(Field):
    
    field_name = "Integer"

    def to_python(self,value):
        return int(value)

class CharField(Field):
    
    field_name = "String"
    
    def to_python(self,value):
        return value

class FloatField(Field):
    field_name = "A float number"
    
    def to_python(self,value):
        return float(value)
    
class ForeignKey(Field):
    field_name = "not defined"
     
    def __init__(self,*args,**kwargs):
        self.pk = kwargs.pop('pk','pk')
        if len(args)<1:
            raise ValueError("You should provide a Model as the first argument.")
        self.model = args[0]
        try:
            if not issubclass(self.model,djangoModel):
                raise TypeError("The first argument should be a django model class.")
        except TypeError,e:
            raise TypeError("The first argument should be a django model class.")
        super(ForeignKey,self).__init__(**kwargs)
    
    def to_python(self,value):
        try:
            return self.model.objects.get(**{self.pk:value})
        except ObjectDoesNotExist, e:
            raise FieldError("No match found for %s" % self.model.__name__)
        