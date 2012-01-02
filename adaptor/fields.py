from lxml import etree

from django.db.models import Model as djangoModel
from django.core.exceptions import ObjectDoesNotExist


class FieldError(ValueError):
    pass


class ForeignKeyFieldError(FieldError):
    def __init__(self, msg, model, value):
        self.model = model
        self.value = value
        self.msg = msg
        super(ForeignKeyFieldError, self).__init__(self.msg)


class FieldValueMissing(FieldError):
    def __init__(self, field_name):
        super(FieldValueMissing, self).__init__("No value found for field %s" % field_name)



class Field(object):
    position = 0

    def __init__(self, **kwargs):
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
        if 'prepare' in kwargs:
            self.prepare = kwargs.pop('prepare')
        if 'keys' in kwargs and isinstance(self, ComposedKeyField):
            self.keys = kwargs.pop('keys')
        if len(kwargs) > 0:
            raise ValueError("Arguments %s unexpected" % kwargs.keys())

    def get_prep_value(self, value):
        try:
            if hasattr(self, "prepare"):
                value = self.prepare(value)
            value = self.to_python(value)
            if hasattr(self, "transform"):
                value = self.transform(value)
            if hasattr(self, "validator"):
                validator = self.validator()
                if not validator.validate(value):
                    raise FieldError(validator.__class__.validation_message)
            return value
        except FieldError, e:
            raise e
        except ValueError, e:
            raise ValueError("Value \'%s\' in columns %d does not match the expected type %s" %
                             (value, self.position + 1, self.__class__.field_name))


class IntegerField(Field):
    field_name = "Integer"

    def to_python(self, value):
        return int(value)


class BooleanField(Field):
    field_name = "Boolean"

    def default_is_true_method(self, value):
        return value.lower() == "true"

    def __init__(self, *args, **kwargs):
        if 'is_true' in kwargs:
            self.is_true_method = kwargs.pop('is_true')
        else:
            self.is_true_method = self.default_is_true_method
        super(BooleanField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        return self.is_true_method(value)


class CharField(Field):
    field_name = "String"

    def to_python(self, value):
        return value


class FloatField(Field):
    field_name = "A float number"

    def to_python(self, value):
        return float(value)


class IgnoredField(Field):
    field_name = "Ignore the value"

class ForeignKey(Field):
    field_name = "not defined"

    def __init__(self, *args, **kwargs):
        self.pk = kwargs.pop('pk', 'pk')
        if len(args) < 1:
            raise ValueError("You should provide a Model as the first argument.")
        self.model = args[0]
        try:
            if not issubclass(self.model, djangoModel):
                raise TypeError("The first argument should be a django model class.")
        except TypeError, e:
            raise TypeError("The first argument should be a django model class.")
        super(ForeignKey, self).__init__(**kwargs)

    def to_python(self, value):
        try:
            return self.model.objects.get(**{self.pk: value})
        except ObjectDoesNotExist, e:
            raise ForeignKeyFieldError("No match found for %s" % self.model.__name__, self.model.__name__, value)


class ComposedKeyField(ForeignKey):
    def to_python(self, value):
        try:
            return self.model.objects.get(**value)
        except ObjectDoesNotExist, e:
            raise ForeignKeyFieldError("No match found for %s" % self.model.__name__, self.model.__name__, value)

class XMLField(Field):
    type_field_class = None

    def __init__(self, *args, **kwargs):
        self.path = kwargs.pop("path")
        self.root = kwargs.pop("root", None)
        self.null = kwargs.pop("null", False)
        self.default = kwargs.pop("default", None)
        if self.default and not self.null:
            raise FieldError("You cannot provide a default without setting the field as nullable")
        self.type_class = self._get_type_field()
        if self.type_class:
            self.type_class.__init__(self, *args, **kwargs)


    def _get_type_field(self):
        base_classes = self.__class__.__bases__
        for base_class in base_classes:
            if issubclass(base_class, Field) and not issubclass(base_class, XMLField):
                return base_class

    def get_prep_value(self, value):
        element = self.root or etree.fromstring(value)
        values = element.xpath(self.path)
        if not values and self.null:
            if self.default is not None:
                parsed_value = self.default
            else:
                return None
        else:
            parsed_value = element.xpath(self.path)[0].text
        return self.type_class.get_prep_value(self, parsed_value)


#    def to_python(self, value):
#        element = self.root or etree.fromstring(value)
#        values = element.xpath(self.path)
#        if not values and self.null:
#            if self.default is not None:
#                parsed_value = self.default
#            else:
#                return None
#        else:
#            parsed_value = element.xpath(self.path)[0].text
#        return self._get_type_field().to_python(self, parsed_value)

    def set_root(self, root):
        self.root = root

class XMLRootField(XMLField):
    def __init__(self, *args, **kwargs):
        super(XMLRootField, self).__init__(*args, **kwargs)
        kwargs['root'] = self

    def get_prep_value(self, value):
        pass

    def to_python(self, value):
        pass

    def get_root(self, value):
        element = self.root or etree.fromstring(value)
        return element.xpath(self.path)


class XMLEmbed(XMLRootField):
    def __init__(self, embed_model):
        self.embed_model = embed_model
        super(XMLEmbed, self).__init__(path=self.embed_model.get_root_field()[1].path)

    def get_prep_value(self, value):
        roots = self.get_root(self.root)
        objects = []
        for root in roots:
            objects.append(self.embed_model(value, element=root))
        return objects

class XMLCharField(XMLField, CharField):
    pass

class XMLIntegerField(XMLField, IntegerField):
    pass

class XMLFloatField(XMLField, FloatField):
    pass

class XMLForeignKey(XMLField, ForeignKey):
    def __init__(self, *args, **kwargs):
        self.nomatch = kwargs.pop("nomatch", False)
        super(XMLForeignKey, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        try:
            return super(XMLForeignKey, self).get_prep_value(value)
        except ForeignKeyFieldError, e:
            if self.nomatch:
                return None
            else:
                raise e

class XMLBooleanField(XMLField, BooleanField):
    pass
