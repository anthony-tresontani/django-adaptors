from django.test import TestCase
from fields import *
from model import CsvModel, CsvDbModel, ImproperlyConfigured
from myTestModel.models import MyModel


class TestCsvModel(CsvModel):
    nom = CharField()
    age = IntegerField()
    taille = FloatField()

    class Meta:
        delimiter = ";"

    test_data = ["Roger", "10", "1.8"]


class TestCsvError(CsvModel):
    nom = CharField()
    age = IntegerField()
    taille = FloatField()

    class Meta:
        delimiter = ";"

    test_data = ["10", "Roger", "1.8"]


class TestCsvSingleData(CsvModel):
    single = CharField()


class TestCsvNoDelimiter(CsvModel):
    nom = CharField()
    age = IntegerField()

    test_data = ["10", "Roger"]


class TestCsvNoField(CsvModel):
    test_data = ["tata", "yoyo"]


class TestCsvMultipleLine(TestCsvModel):
    nom = CharField()
    age = IntegerField()
    taille = FloatField()

    test_data = ["Roger;10;1.8", "Janette;12;1.7"]


class TestCsvDBModel(TestCsvModel):
    class Meta:
        delimiter = ";"
        dbModel = MyModel


class TestCsvDBUnmatchingModel(CsvModel):
    name = CharField(match='nom')
    age = IntegerField()
    taille = FloatField()

    class Meta:
        delimiter = ";"
        dbModel = MyModel


class TestCsvWithHeader(TestCsvModel):
    class Meta:
        delimiter = ";"
        has_header = True
        dbModel = MyModel

    test_data = ["Name;Age;length", "Roger;10;1.8", "Janette;12;1.7"]


class TestCsvExitOnFailure(TestCsvModel):
    class Meta:
        silent_failure = True
        delimiter = ";"
        dbModel = MyModel

    test_data = ["Roger;Error;1.8", "Janette;12;1.7"]
    
class TestCsvDBOnlyModel(CsvDbModel):
    class Meta:
        dbModel = MyModel
        delimiter = ";"
        exclude = ['id']
        
    test_data = ["Janette;12;1.7","Roger;18;1.8"]


class TestCsvImporter(TestCase):
    def test_has_delimiter(self):
        self.assertTrue(TestCsvModel.has_delimiter())
        self.assertFalse(TestCsvNoDelimiter.has_delimiter())

    def test_is_db_model(self):
        self.assertFalse(TestCsvModel.is_db_model())
        self.assertTrue(TestCsvDBModel.is_db_model())

    def test_basic(self):
        test = TestCsvModel(data=TestCsvModel.test_data)
        self.assertEquals(test.nom, 'Roger')
        self.assertEquals(test.age, 10)
        self.assertEquals(test.taille, 1.8)

    def test_value_error(self):
        self.assertRaises(ValueError, TestCsvError, data=TestCsvError.test_data)

    def test_single(self):
        test = TestCsvSingleData(data=["RogerAgain"])
        self.assertEquals(test.single, "RogerAgain")

    def test_no_delimiter(self):
        self.assertRaises(ImproperlyConfigured, TestCsvNoDelimiter, data=TestCsvError.test_data)

    def test_no_field(self):
        self.assertRaises(ImproperlyConfigured, TestCsvNoField, data=TestCsvNoField.test_data)

    def test_multiple_lines(self):
        test = TestCsvMultipleLine.import_data(data=TestCsvMultipleLine.test_data)
        line1 = test[0]
        self.assertEquals(line1.nom, 'Roger')
        self.assertEquals(line1.age, 10)
        self.assertEquals(line1.taille, 1.8)

        line2 = test[1]
        self.assertEquals(line2.nom, 'Janette')
        self.assertEquals(line2.age, 12)
        self.assertEquals(line2.taille, 1.7)

        index = 0
        for line in test:
            self.assertEquals(line, test[index])
            index += 1

    def test_real_file(self):
        test = TestCsvModel.import_data(open("test/csv1.csv", 'r'))
        line1 = test[0]
        self.assertEquals(line1.nom, 'Roger')
        self.assertEquals(line1.age, 10)
        self.assertEquals(line1.taille, 1.8)

    def test_db_model(self):
        test = TestCsvDBModel.import_data(open("test/csv2.csv", 'r'))
        self.assertEquals(MyModel.objects.all().count(), 2)

    def test_db_unmatching_model(self):
        test = TestCsvDBUnmatchingModel.import_data(open("test/csv1.csv", 'r'))
        self.assertEquals(MyModel.objects.all().count(), 1)

    def test_field_unexpected_attributes(self):
        def create_unexpected_model():
            #class TestCsvUnexpectedAttributes(CsvModel):
            #    name = CharField(unexpected=True)
            return type('TestCsvDBUnmatchingModel', CsvModel, {'name': CharField(unexpected=True)})

        self.assertRaises(ValueError, create_unexpected_model)

    def test_exit_on_failure(self):
        test = TestCsvExitOnFailure.import_data(TestCsvExitOnFailure.test_data)
        self.assertEquals(MyModel.objects.all().count(), 1)

    def test_with_header(self):
        test = TestCsvWithHeader.import_data(TestCsvWithHeader.test_data)
        self.assertEquals(MyModel.objects.all().count(), 2)
        
    def test_direct_to_db(self):
        test = TestCsvDBOnlyModel.import_data(TestCsvDBOnlyModel.test_data)
        self.assertEquals(MyModel.objects.all().count(), 2)
        myModel = MyModel.objects.all()[0]
        self.assertEquals(myModel.nom, "Janette")
        self.assertEquals(myModel.age, 12)
        self.assertEquals(myModel.taille, 1.7)
        




        

