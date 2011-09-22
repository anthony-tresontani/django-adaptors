from django.db.models import Model as djangoModel

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
        if len(kwargs)>0:
            raise ValueError("Arguments %s unexpected" % kwargs.keys())

    def get_prep_value(self,value):
        try:
            value = self.to_python(value)
            if hasattr(self,"transform"):
                return self.transform(value)
            return value
        except ValueError:
            raise ValueError("Value \'%s\' in columns %d does not match the expected type %s" % (value,self.position+1,self.__class__))


class IntegerField(Field):

    def to_python(self,value):
        return int(value)

class CharField(Field):
    def to_python(self,value):
        return value

class FloatField(Field):
    def to_python(self,value):
        return float(value)
    
class ForeignKey(Field): 
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
        return self.model.objects.get(**{self.pk:value})
        