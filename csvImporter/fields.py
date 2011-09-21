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
        if len(kwargs)>0:
            raise ValueError("Arguments %s unexpected" % kwargs.keys())

    def get_value(self,value):
        try:
            return self.prep_value(value)
        except ValueError:
            raise ValueError("Value %s in columns %d does not match the expected type %s" % (value,self.position+1,self.__class__))


class IntegerField(Field):

    def prep_value(self,value):
        return int(value)

class CharField(Field):
    def prep_value(self,value):
        return value

class FloatField(Field):
    def prep_value(self,value):
        return float(value)