from django.test import TestCase
from fields import *
from model import CsvModel, CsvDbModel, ImproperlyConfigured
from myTestModel.models import MyModel, MyModel2, MyModelWithForeign, OtherForeign


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
#        exclude = ['id']
        
    test_data = ["Janette;12;1.7","Roger;18;1.8"]

        
class TestCsvDbForeignInvalid(CsvDbModel):
    foreign = ForeignKey(MyModel)
    
    class Meta:
        dbModel = MyModelWithForeign


class TestCsvImporter(TestCase):
    def test_has_delimiter(self):
        self.assertTrue(TestCsvModel.has_class_delimiter())
        self.assertFalse(TestCsvNoDelimiter.has_class_delimiter())

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
        file = open("test/csv1.csv")
        test = TestCsvModel.import_from_file(file)
        line1 = test[0]
        self.assertEquals(line1.nom, 'Roger')
        self.assertEquals(line1.age, 10)
        self.assertEquals(line1.taille, 1.8)

    def test_db_model(self):
        test = TestCsvDBModel.import_from_filename("test/csv2.csv")
        self.assertEquals(MyModel.objects.all().count(), 2)

    def test_db_unmatching_model(self):
        test = TestCsvDBUnmatchingModel.import_from_filename("test/csv1.csv")
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
        class TestCsvWithHeader(TestCsvModel):
            class Meta:
                delimiter = ";"
                has_header = True
                dbModel = MyModel

            test_data = ["Name;Age;length", "Roger;10;1.8", "Janette;12;1.7"]

        
        
        test = TestCsvWithHeader.import_data(TestCsvWithHeader.test_data)
        self.assertEquals(MyModel.objects.all().count(), 2)
        
    def test_direct_to_db(self):
        test = TestCsvDBOnlyModel.import_data(TestCsvDBOnlyModel.test_data)
        self.assertEquals(MyModel.objects.all().count(), 2)
        myModel = MyModel.objects.all()[0]
        self.assertEquals(myModel.nom, "Janette")
        self.assertEquals(myModel.age, 12)
        self.assertEquals(myModel.taille, 1.7)
        
    def test_foreign_key_model(self):
        class TestCsvDbForeign(CsvModel):
            foreign = ForeignKey(MyModel)
    
            class Meta:
                dbModel = MyModelWithForeign
                delimiter = ","
        
        my_model = MyModel.objects.create(nom="Gigi", age=10, taille= 1.2)
        test = TestCsvDbForeign.import_data(["%d" % my_model.id])
        self.assertEquals(MyModelWithForeign.objects.all().count(), 1)
        
        
    def test_with_invalid_foreign(self):
        self.assertRaises(ImproperlyConfigured,TestCsvDbForeignInvalid,[1])
        
    def test_transform_foreign(self):
        class TestCsvDbForeignFollow(CsvModel):
            foreign_csv = ForeignKey(MyModelWithForeign,transform= lambda x:x.foreign,match="foreign")
    
            class Meta:
                dbModel = OtherForeign
                delimiter = ","
        
        my_model = MyModel.objects.create(nom="Gigi", age=10, taille= 1.2)
        foreign = MyModelWithForeign.objects.create(foreign=my_model)
        test = TestCsvDbForeignFollow.import_data(["%d" % foreign.id] )
        self.assertEquals(my_model, test[0].foreign_csv)
        
    def test_import_from_file_sniffer(self):
        
        class TestCsvWithHeader(TestCsvModel):
            class Meta:
                dbModel = MyModel

        test = TestCsvWithHeader.import_from_filename("test/csv3.csv")
        self.assertEquals(MyModel.objects.all().count(), 23)

class TestFields(TestCase):
    
    def test_foreign_key(self):
        self.assertRaises(ValueError,ForeignKey)
        self.assertRaises(TypeError,ForeignKey,10)
        field = ForeignKey(MyModel)
        myModel = MyModel.objects.create(nom="jojo",age="10",taille=1.5)
        self.assertEquals(field.to_python(myModel.id), myModel)
        
    def test_foreign_other_pk(self):
        field = ForeignKey(MyModel2,pk="other_pk")
        myModel2 = MyModel2.objects.create(other_pk=10)
        self.assertEquals(field.to_python(myModel2.other_pk), myModel2)
        
class TestImporter(TestCase):
    
    
    def test_extra_fields(self):
        
        class TestCsvExtraFields(CsvModel):
            nom = CharField()
            age = IntegerField()
            taille = FloatField()
            extra_value = CharField()
            
            class Meta:
                delimiter = ";"
                
            test_data = ["Janette;12;1.7","Roger;18;1.8"]
                
        test = TestCsvExtraFields.import_data(TestCsvExtraFields.test_data,extra_fields=["extra"])
        self.assertEquals(test[0].extra_value, "extra")
        self.assertEquals(test[1].extra_value, "extra")
        
    def test_positionnal_extra_value(self):
        
        class TestCsvExtraFieldsPositionnal(CsvModel):
            extra_value = CharField()
            nom = CharField()
            age = IntegerField()
            taille = FloatField()
            
            class Meta:
                delimiter = ";"
                
            test_data = ["Janette;12;1.7","Roger;18;1.8"]
                
        test = TestCsvExtraFieldsPositionnal.import_data(TestCsvExtraFieldsPositionnal.test_data,extra_fields=[{'value':"extra",'position':0}])
        self.assertEquals(test[0].extra_value, "extra")
        self.assertEquals(test[1].extra_value, "extra")
        
        

        

