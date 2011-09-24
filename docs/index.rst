.. CSV Importer documentation master file, created by
   sphinx-quickstart on Sat Sep 24 18:18:56 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to CSV Importer's documentation!
========================================

Contents: **CSV importer** is a tool which allow you to transform easily a csv file into a python object or a django model instance.
It is based on a django-style declarative model.


.. toctree::
   :maxdepth: 2


Basic sample
------------

Here is a basic sample:

>>> class MyCSvModel(CsvModel):
>>>    name = CharField()
>>>    age = IntegerField()
>>>    length = FloatField()
>>> 
>>>    class Meta:
>>>        delimiter = ";"

You declare a MyCsvModel which will match to a csv file like this:
"Anthony;27;1.75"

To import the file or any iterable object, just do:

>>> my_csv_list = MyCsvModel.import_data(data = open("my_csv_file_name.csv"))
>>> first_line = my_csv_list[0]
>>> first_line.age
27

Without an explicit declaration, data and columns are matched in the same order:

- Anthony --> Column 0 --> Field 0 --> name
- 27      --> Column 1 --> Field 1 --> age
- 1.75    --> Column 2 --> Field 2 --> length

Django Model
------------

If you now want to interact with a django model, you just have to add a **dbModel** option to the class meta.

>>> from model import CsvModel
>>>
>>> class MyCSvModel(CsvModel):
>>>    name = CharField()
>>>    age = IntegerField()
>>>    length = FloatField()
>>>
>>>    class Meta:
>>>        delimiter = ";"
>>>        dbModel = Person

That will automatically match to the following django model.

>>> class Person(models.Model):
>>>    name = CharField(max_length = 100)
>>>    age = IntegerField()
>>>    length = FloatField()

If field names of your Csv model does not match the field names of your django model, you can manage this with the match keyword:

>>> class MyCSvModel(CsvModel):
>>>    fullname = CharField(match = "name")
...

If you don't want to have to re-declare a CSV model whereas the Django model already exist, use a CsvDbModel.

>>> from my_projects.models import Person
>>> from csv_importer.model import CsvDbModel
>>>
>>> class MyCsvModel(CsvDbModel):
>>>
>>>     class Meta:
>>>        dbModel = Person
>>>        delimiter = ";"

*The django model should be imported in the model*

Fields
------

Fields available are:

- **IntegerField** : return an int
- **FloatField** : return a float
- **CharField** : return a string
- **ForeignKey** : return a django model object

Options :

You can give, as argument, the following options:

- `row_num` : define the position in the file for this field
- `match` : define the django model name matching this field
- `transform` : Apply the function before returning the result

Here is an example of a way to use the transform attribute.

>>> class MyCsvModel(CsvModel):
>>>
>>>     user  = ForeignKey(transform = lambda user: user.username)

ForeignKey has an additional argument `pk` which allow you to define on which value the object will be retrieved.


Meta options
------------

`delimiter`
    define the delimiter of the csv file

`has_header`
    Skip the first line if True

`dbModel`
    If defined, the importer will create an instance of this model

`silent_failure`
    If set to True, an error in a imported line will not stop the loading

`exclude`
    CsvDbModel only. To do take into account the django field of the django model defined in this list

Importer option
---------------

When importing data, you can add an optional argument `extra_fields` which is a string or a list.
This allow to add a value to any line of the csv file before the loading.