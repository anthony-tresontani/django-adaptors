from datetime import datetime
from decimal import Decimal
from lxml import etree

from django.db.models import Model as djangoModel
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from adaptor import exceptions


class AllChoices(object):
    def __contains__(self, value):
        return True


class AlwaysValidValidator(object):
    def validate(self, val):
        return True


class BaseField(object):
    def __init__(self, kwargs):
        self.transform = kwargs.pop('transform', lambda val:val)

class Field(BaseField):
    position = 0

    def __init__(self, **kwargs):
        super(Field, self).__init__(kwargs)
        self.null = kwargs.pop("null", False)
        self.default = kwargs.pop("default", None)
        if self.default and not self.null:
            raise exceptions.FieldError("You cannot provide a default without setting the field as nullable")
        if 'row_num' in kwargs:
            self.position = kwargs.pop('row_num')
        else:
            self.position = Field.position
            Field.position += 1
        if 'match' in kwargs:
            self.match = kwargs.pop('match')
        self.validator = kwargs.pop('validator', AlwaysValidValidator)
        if 'multiple' in kwargs:
            self.has_multiple = kwargs.pop('multiple')
        self.prepare = kwargs.pop('prepare', lambda val:val)
        if 'keys' in kwargs and isinstance(self, ComposedKeyField):
            self.keys = kwargs.pop('keys')
        self.choices= kwargs.pop('choices', AllChoices())
        if len(kwargs) > 0:
            raise ValueError("Arguments %s unexpected" % kwargs.keys())

    def get_transform_method(self, instance):
        """ Look for transform_<field_name>, else look for the transform parameter, else identity method """
        transform_method = "transform_" + getattr(self, "fieldname", self.field_name)
        transform = getattr(instance, transform_method, self.transform)
        return transform

    def get_prep_value(self, value, instance=None):
        try:
            value = self.prepare(value)
            if not value and self.null and self.default is not None:
                value = self.default
            else:
                value = self.to_python(value)
            if value not in self.choices:
                if not self.null:
                    raise exceptions.ChoiceError("Value \'%s\' does not belong to %s" % (value, self.choices))
                value = None 
            transform = self.get_transform_method(instance)
            value = transform(value)
            if not self.validator().validate(value):
                raise exceptions.FieldError(self.validator.validation_message)
            return value
        except exceptions.ChoiceError:
            raise 
        except exceptions.FieldError:
            raise
        except ValueError:
            self.raise_type_error(value)

    def raise_type_error(self, value):
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


class DateField(Field):
    field_name = "Date"

    def __init__(self, *args, **kwargs):
        if 'format' in kwargs:
            self.format = kwargs.pop('format')
        else:
            self.format = "%d/%m/%Y"
        super(DateField, self).__init__(*args, **kwargs)


    def to_python(self, value):
        return datetime.strptime(value, self.format)

class DecimalField(Field):
    field_name = "A Decimal number"

    def to_python(self, value):
        return Decimal(value)


class FloatField(Field):
    field_name = "A float number"

    def to_python(self, value):
        return float(value)


class IgnoredField(Field):
    field_name = "Ignore the value"


class DjangoModelField(Field):
    field_name = "not defined"

    def __init__(self, *args, **kwargs):
        self.pk = kwargs.pop('pk', 'pk')
        if len(args) < 1:
            raise ValueError("You should provide a Model as the first argument.")
        self.model = args[0]
        try:
            if not issubclass(self.model, djangoModel):
                raise TypeError("The first argument should be a django model class.")
        except TypeError:
            raise TypeError("The first argument should be a django model class.")
        super(DjangoModelField, self).__init__(**kwargs)

    def to_python(self, value):
        try:
            return self.model.objects.get(**{self.pk: value})
        except ObjectDoesNotExist:
            raise exceptions.ForeignKeyFieldError("No match found for %s" % self.model.__name__, self.model.__name__, value)
        except MultipleObjectsReturned:
            raise exceptions.ForeignKeyFieldError("Multiple match found for %s" % self.model.__name__, self.model.__name__, value)


class ComposedKeyField(DjangoModelField):
    def to_python(self, value):
        try:
            return self.model.objects.get(**value)
        except ObjectDoesNotExist:
            raise exceptions.ForeignKeyFieldError("No match found for %s" % self.model.__name__, self.model.__name__, value)


class XMLField(Field):
    type_field_class = None

    def __init__(self, *args, **kwargs):
        self.path = kwargs.pop("path")
        self.root = kwargs.pop("root", None)
        self.attribute = kwargs.pop("attribute", None)
        self.type_class = self._get_type_field()
        if self.type_class:
            self.type_class.__init__(self, *args, **kwargs)
        else:
            BaseField.__init__(self, kwargs)


    def _get_type_field(self):
        base_classes = self.__class__.__bases__
        for base_class in base_classes:
            if issubclass(base_class, Field) and not issubclass(base_class, XMLField):
                return base_class

    def get_prep_value(self, value, instance=None):
        from lxml import etree
        element = self.root if self.root is not None else etree.fromstring(value)
        values = element.xpath(self.path)
        if not values and self.null:
            if self.default is not None:
                parsed_value = self.default
            else:
                return None
        else:
            if not self.attribute:
                parsed_value = element.xpath(self.path)[0].text
            else:
                parsed_value = element.xpath(self.path)[0].get(self.attribute)
        return self.type_class.get_prep_value(self, parsed_value, instance=instance)

    def set_root(self, root):
        self.root = root

    def raise_type_error(self, value):
        raise ValueError("Value \'%s\' does not match the expected type %s" %
                             (value, self.__class__.field_name))



class XMLRootField(XMLField):
    def __init__(self, *args, **kwargs):
        super(XMLRootField, self).__init__(*args, **kwargs)
        kwargs['root'] = self

    def get_prep_value(self, value, instance=None):
        pass

    def to_python(self, value):
        pass

    def get_root(self, value):
        from lxml import etree
        element = self.root if self.root is not None else etree.fromstring(value)
        return element.xpath(self.path)


class XMLEmbed(XMLRootField):
    field_name = "not defined"

    def __init__(self, embed_model):
        self.embed_model = embed_model
        super(XMLEmbed, self).__init__(path=self.embed_model.get_root_field()[1].path)

    def get_prep_value(self, value, instance=None):
        roots = self.get_root(self.root)
        objects = []
        for root in roots:
            objects.append(self.embed_model(value, element=root))
        transform = self.get_transform_method(instance)
        objects = transform(objects)
        return objects


class XMLCharField(XMLField, CharField):
    pass


class XMLIntegerField(XMLField, IntegerField):
    pass


class XMLDecimalField(XMLField, DecimalField):
    pass

class XMLFloatField(XMLField, FloatField):
    pass


class XMLDjangoModelField(XMLField, DjangoModelField):
    def __init__(self, *args, **kwargs):
        self.nomatch = kwargs.pop("nomatch", False)
        super(XMLDjangoModelField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value, instance=None):
        try:
            return super(XMLDjangoModelField, self).get_prep_value(value, instance=instance)
        except exceptions.ForeignKeyFieldError, e:
            if self.nomatch:
                return None
            else:
                raise e


class XMLBooleanField(XMLField, BooleanField):
    pass


class XMLDateField(XMLField, DateField):
    pass
