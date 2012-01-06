from django.test import TestCase
from fields import *
from model import CsvModel, CsvDbModel, ImproperlyConfigured,\
    CsvException, CsvDataException, TabularLayout, SkipRow,\
    GroupedCsvModel, XMLModel
from myTestModel.models import *


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

    test_data = ["Janette;12;1.7", "Roger;18;1.8"]


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


    def test_get_object(self):
        class TestCsvGetObject(CsvModel):
            nom = CharField()
            age = IntegerField()
            taille = FloatField()

            class Meta:
                delimiter = ";"
                dbModel = MyModel

        test_data = ["Janette;12;1.7"]
        test = TestCsvGetObject.import_data(test_data)
        obj = MyModel.objects.all()[0]
        self.assertEquals(obj, test[0].get_object())


    def test_db_unmatching_model(self):
        class TestCsvDBUnmatchingModel(CsvModel):
            name = CharField(match='nom')
            age = IntegerField()
            taille = FloatField()

            class Meta:
                delimiter = ";"
                dbModel = MyModel


        test = TestCsvDBUnmatchingModel.import_from_filename("test/csv1.csv")
        self.assertEquals(MyModel.objects.all().count(), 1)

        obj = test[0].get_object()
        test_csv = TestCsvDBUnmatchingModel(obj)
        self.assertEquals(test_csv.name, obj.nom)
        self.assertEquals(test[0].export(), u"Roger;10;1.8")

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

        my_model = MyModel.objects.create(nom="Gigi", age=10, taille=1.2)
        test = TestCsvDbForeign.import_data(["%d" % my_model.id])
        self.assertEquals(MyModelWithForeign.objects.all().count(), 1)


    def test_with_invalid_foreign(self):
        self.assertRaises(ImproperlyConfigured, TestCsvDbForeignInvalid, [1])

    def test_transform_foreign(self):
        class TestCsvDbForeignFollow(CsvModel):
            foreign_csv = ForeignKey(MyModelWithForeign, transform=lambda x:x.foreign, match="foreign")

            class Meta:
                dbModel = OtherForeign
                delimiter = ","

        my_model = MyModel.objects.create(nom="Gigi", age=10, taille=1.2)
        foreign = MyModelWithForeign.objects.create(foreign=my_model)
        test = TestCsvDbForeignFollow.import_data(["%d" % foreign.id])
        self.assertEquals(my_model, test[0].foreign_csv)

    def test_import_from_file_sniffer(self):
        class TestCsvWithHeader(TestCsvModel):
            class Meta:
                dbModel = MyModel

        test = TestCsvWithHeader.import_from_filename("test/csv3.csv")
        self.assertEquals(MyModel.objects.all().count(), 23)

    def test_error_message_foreign(self):
        class TestCsvDbForeign(CsvModel):
            foreign = ForeignKey(MyModel)

            class Meta:
                dbModel = MyModelWithForeign
                delimiter = ","

        test_data_template = "%d,10,1"
        my_model = MyModel.objects.create(nom="Gigi", age=10, taille=1.2)
        data = [test_data_template % my_model.id, test_data_template % (my_model.id + 999)]
        try:
            test = TestCsvDbForeign.import_data(data)
        except CsvException, e:
            self.assertEquals(e.message, u'Line 2: No match found for MyModel')
        else:
            self.assertTrue(False, "No valueError raised")

    def test_error_message_too_many_field(self):
        try:
            test = TestCsvModel.import_data(['1,error,12'])
        except CsvException, e:
            self.assertEquals(e.message, u'Line 1: Number of fields invalid')
        else:
            self.assertTrue(False, "No valueError raised")

    def test_error_message_integer_field(self):
        try:
            test = TestCsvModel.import_data(['1;error;12'])
        except CsvException, e:
            self.assertEquals(e.message,
                              u"Line 1: Value 'error' in columns 2 does not match the expected type Integer")
        else:
            self.assertTrue(False, "No valueError raised")


    def test_validator(self):
        class CsvValidator(CsvModel):
            class Meta:
                delimiter = ";"

            class Validate:
                validation_message = "Your value should be 10"

                def validate(self, value):
                    return value == 10

            age = IntegerField(validator=Validate)

        self.assertRaises(CsvDataException, CsvValidator.import_data, ['11'])
        try:
            CsvValidator.import_data(['10'])
        except CsvDataException, e:
            self.assertTrue(False, "No exception should be raised")
        self.assertTrue(True)


    def test_multiple_fields(self):
        class CsvMultiple(CsvModel):
            nom = CharField()
            note = IntegerField(multiple=True)

            class Meta:
                delimiter = ";"
                dbModel = MultipleModel

        test_data = ["josette;18;12;8"]

        test = CsvMultiple.import_data(test_data)
        self.assertEquals(MultipleModel.objects.count(), 3)


    def test_tabular_layout(self):
        class CsvTabular(CsvModel):
            nom = CharField()
            age = IntegerField()
            taille = FloatField()

            class Meta:
                delimiter = ";"
                layout = TabularLayout
                dbModel = MyModel

        test_data = [";8;12;18", "Janette;1.2;1.4;1.6", "popeye;0.8;1.0;1.3"]
        test = CsvTabular.import_data(test_data)
        self.assertEquals(MyModel.objects.all().count(), 6)

    def test_prepare(self):
        def upper(name):
            return name.upper()

        class CsvPrepare(CsvModel):
            nom = CharField(prepare=upper)
            age = IntegerField()
            taille = FloatField()

            class Meta:
                delimiter = ";"
                dbModel = MyModel

        test_data = ["Janette;12;1.7", "Roger;18;1.8"]
        test = CsvPrepare.import_data(test_data)
        self.assertEquals(test[0].nom, "JANETTE")
        self.assertEquals(test[1].nom, "ROGER")

    def test_ignore_field(self):
        class IgnoreCsv(CsvModel):
            nom = CharField()
            ignored = IgnoredField()
            age = IntegerField()
            taille = FloatField()


            class Meta:
                delimiter = ";"
                dbModel = MyModel

        test_data = ["Janette;Dont care;12;1.7", "Roger;Dont care;18;1.8"]
        test = IgnoreCsv.import_data(test_data)
        self.assertEquals(MyModel.objects.all().count(), 2)

    def test_skip_row(self):
        def skip_janette(name):
            if name == "Janette":
                raise SkipRow()
            return name

        class SkipRowCsv(CsvModel):
            nom = CharField(prepare=skip_janette)
            age = IntegerField()
            taille = FloatField()

            class Meta:
                delimiter = ";"
                dbModel = MyModel

        test_data = ["Janette;12;1.7", "Roger;18;1.8"]
        test = SkipRowCsv.import_data(test_data)
        self.assertEquals(MyModel.objects.all().count(), 1)

    def test_multiple_key_foreign(self):
        class ComposedForeignKeyCsv(CsvModel):
            key_1 = IntegerField()
            key_2 = IntegerField()
            composed_key_foreign = ComposedKeyField(ComposedKeyForeign, keys=["key_1", "key_2"])

            class Meta:
                delimiter = ";"
                dbModel = ComposedKey

        c0 = ComposedKeyForeign.objects.create(key_1=1, key_2=1)
        c1 = ComposedKeyForeign.objects.create(key_1=1, key_2=2)
        test_data = ["1;1", "1;2"]
        test = ComposedForeignKeyCsv.import_data(test_data)
        self.assertEquals(c0, test[0].composed_key_foreign)
        self.assertEquals(c1, test[1].composed_key_foreign)

    def test_update(self):
        class TestUpdateCsv(CsvModel):
            nom = CharField()
            age = IntegerField()
            taille = FloatField()

            class Meta:
                dbModel = MyModel
                delimiter = ";"
                update = {'keys': ["nom", "age"]}

        test_data = ["Janette;12;1.0", "Janette;12;2.0"]
        self.assertEquals(MyModel.objects.count(), 0)
        test = TestUpdateCsv.import_data(test_data)
        self.assertEquals(MyModel.objects.count(), 1)
        self.assertEquals(MyModel.objects.all()[0].taille, 2.0)

    def test_update_only(self):
        class TestUpdateOnlyCsv(CsvModel):
            nom = CharField()
            age = IntegerField()
            taille = FloatField()
            poids = FloatField()

            class Meta:
                dbModel = MyModelBis
                delimiter = ";"
                update = {'keys': ["nom", "age"], 'update': ['poids']}

        test_data = ["Janette;12;1.0;1.0", "Janette;12;2.0;2.0"]
        self.assertEquals(MyModelBis.objects.count(), 0)
        test = TestUpdateOnlyCsv.import_data(test_data)
        self.assertEquals(MyModelBis.objects.count(), 1)
        self.assertEquals(MyModelBis.objects.all()[0].taille, 1.0)
        self.assertEquals(MyModelBis.objects.all()[0].poids, 2.0)


    def test_update_and_extra(self):
        class TestUpdateOnlyExtraCsv(CsvModel):
            nom = CharField()
            age = IntegerField()
            taille = FloatField()
            poids = FloatField()
            bool = BooleanField()

            class Meta:
                dbModel = MyModelTer
                delimiter = ";"
                update = {'keys': ["nom", "age"], 'update': ['poids']}


        test_data = ["Janette;12;1.0;1.0", "Janette;12;2.0;2.0"]
        test = TestUpdateOnlyExtraCsv.import_data(test_data, extra_fields=["True"])
        self.assertEquals(MyModelTer.objects.count(), 1)
        self.assertEquals(MyModelTer.objects.all()[0].taille, 1.0)
        self.assertEquals(MyModelTer.objects.all()[0].poids, 2.0)
        self.assertTrue(MyModelTer.objects.all()[0].bool)

        test_data2 = ["Jojo;11;1.0;1.0"]
        test = TestUpdateOnlyExtraCsv.import_data(test_data2, extra_fields=["false"])
        self.assertEquals(test[0].bool, False)

        test = TestUpdateOnlyExtraCsv.import_data(test_data2, extra_fields=["True"])
        self.assertFalse(MyModelTer.objects.get(nom="Jojo").bool)

    def test_match(self):
        class TestMatchCsv(CsvModel):
            text = CharField(match=["text_1", "text_2"])

            class Meta:
                dbModel = MyDualModel
                delimiter = ";"

        test_data = ["my data"]
        test = TestMatchCsv.import_data(test_data)
        self.assertEquals(MyDualModel.objects.count(), 1)

        obj = MyDualModel.objects.all()[0]
        self.assertEquals(obj.text_1, "my data")
        self.assertEquals(obj.text_2, "my data")


class TestGroupCsv(TestCase):
    def test_simple_group(self):
        class TestCsv1(CsvModel):
            first_name = CharField()

            class Meta:
                dbModel = FirstNameModel

        class TestCsv2(CsvModel):
            last_name = CharField()

            class Meta:
                dbModel = LastNameModel

        class TestGroupedCsv(GroupedCsvModel):
            csv_models = [TestCsv1, TestCsv2]

            class Meta:
                delimiter = ";"

        test_data = ["jojo;lafrite"]
        test = TestGroupedCsv.import_data(test_data)
        self.assertEquals(FirstNameModel.objects.count(), 1)
        self.assertEquals(FirstNameModel.objects.all()[0].first_name, "jojo")

        self.assertEquals(LastNameModel.objects.count(), 1)
        self.assertEquals(LastNameModel.objects.all()[0].last_name, "lafrite")


    def test_extra_group(self):
        class TestCsvFirstName(CsvModel):
            first_name = CharField()

            class Meta:
                dbModel = FirstNameModel

        class TestCsvLastName(CsvModel):
            foreign = ForeignKey(FirstNameModel)
            last_name = CharField()

            class Meta:
                dbModel = LastNameModelWithForeign

        class TestGroupedCsv(GroupedCsvModel):
            csv_models = [{"model": TestCsvFirstName, "name": "first"},
                    {"model": TestCsvLastName, "name": "last",
                     "use": {"name": "first",
                             "as": "foreign"}
                }
            ]

            class Meta:
                delimiter = ";"

        test_data = ["jojo;lafrite"]
        test = TestGroupedCsv.import_data(test_data)
        self.assertEquals(FirstNameModel.objects.count(), 1)
        self.assertEquals(FirstNameModel.objects.all()[0].first_name, "jojo")

        self.assertEquals(LastNameModelWithForeign.objects.count(), 1)
        self.assertEquals(LastNameModelWithForeign.objects.all()[0].last_name, "lafrite")


class TestFields(TestCase):
    def test_foreign_key(self):
        self.assertRaises(ValueError, ForeignKey)
        self.assertRaises(TypeError, ForeignKey, 10)
        field = ForeignKey(MyModel)
        myModel = MyModel.objects.create(nom="jojo", age="10", taille=1.5)
        self.assertEquals(field.to_python(myModel.id), myModel)

    def test_foreign_other_pk(self):
        field = ForeignKey(MyModel2, pk="other_pk")
        myModel2 = MyModel2.objects.create(other_pk=10)
        self.assertEquals(field.to_python(myModel2.other_pk), myModel2)

    def test_error_message(self):
        field = ForeignKey(MyModel2, pk="other_pk")
        myModel2 = MyModel2.objects.create(other_pk=999)
        try:
            field.to_python(666)
        except ValueError, e:
            self.assertEquals(e.message, 'No match found for MyModel2')
        else:
            self.assertTrue(False, "No exception raised")
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

            test_data = ["Janette;12;1.7", "Roger;18;1.8"]

        test = TestCsvExtraFields.import_data(TestCsvExtraFields.test_data, extra_fields=["extra"])
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

            test_data = ["Janette;12;1.7", "Roger;18;1.8"]

        test = TestCsvExtraFieldsPositionnal.import_data(TestCsvExtraFieldsPositionnal.test_data,
                                                         extra_fields=[{'value': "extra", 'position': 0}])
        self.assertEquals(test[0].extra_value, "extra")
        self.assertEquals(test[1].extra_value, "extra")


class TestExport(TestCase):
    def test_export(self):
        class TestCsvModel(CsvModel):
            nom = CharField()
            age = IntegerField()
            taille = FloatField()

            class Meta:
                delimiter = ";"
                dbModel = MyModel


        my_obj = MyModel.objects.create(nom="Jojo", age=18, taille=1.8)
        test = TestCsvModel(my_obj)
        self.assertEquals(test.nom, my_obj.nom)
        self.assertEquals(test.age, my_obj.age)
        self.assertEquals(test.taille, my_obj.taille)

        self.assertEquals(test.export(), u"Jojo;18;1.8")

        
class TestXMLImporter(TestCase):

    def test_extract_xml_data_simplest_case(self):
        xml = "<name>jojo</name>"
        field = XMLCharField(path="/name", root=None)
        self.assertEquals(field.get_prep_value(xml), "jojo")

    def test_extract_xml_data_integer(self):
        xml = "<data><name>jojo</name><length>2</length></data>"
        char_field = XMLCharField(path="name", root=None)
        int_field = XMLIntegerField(path="length", root=None)
        self.assertEquals(char_field.get_prep_value(xml), "jojo")
        self.assertEquals(int_field.get_prep_value(xml), 2)

    def test_extract_xml_data_float(self):
        xml = "<data><name>jojo</name><length>2.0</length></data>"
        float_field = XMLFloatField(path="length", root=None)
        self.assertEquals(float_field.get_prep_value(xml), 2.0)

    def test_transform(self):
        xml = "<data><name>jojo</name><length>2.0</length></data>"
        float_field = XMLFloatField(path="length", transform=lambda x:x + 1, root=None)
        self.assertEquals(float_field.get_prep_value(xml), 3.0)

    def test_simple_xml_model(self):
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="person")
            name = XMLCharField(path="name")
            age = XMLIntegerField(path="age")

        xmldata = """<data>
                        <person>
                            <name>Jojo</name>
                            <age>14</age>
                        </person>
                        <person>
                            <name>Gigi</name>
                            <age>12</age>
                        </person>
                     </data>"""
        test = TestXMLModel.import_data(xmldata)
        jojo = test[0]
        self.assertEquals(jojo.name, "Jojo")
        self.assertEquals(jojo.age, 14)

        gigi = test[1]
        self.assertEquals(gigi.name, "Gigi")
        self.assertEquals(gigi.age, 12)


    def test_missing_value(self):
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="person")
            name = XMLCharField(path="name")
            age = XMLIntegerField(path="age")

        xmldata = """<data>
                        <person>
                            <name>Jojo</name>
                            <age>14</age>
                        </person>
                        <person>
                            <name>Gigi</name>
                        </person>
                     </data>"""
        self.assertRaises(FieldValueMissing, TestXMLModel.import_data, xmldata)


    def test_null_value(self):
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="person")
            name = XMLCharField(path="name")
            age = XMLIntegerField(path="age", null=True)

        xmldata = """<data>
                        <person>
                            <name>Jojo</name>
                            <age>14</age>
                        </person>
                        <person>
                            <name>Gigi</name>
                        </person>
                     </data>"""
        test = TestXMLModel.import_data(xmldata)
        jojo = test[0]
        self.assertEquals(jojo.name, "Jojo")
        self.assertEquals(jojo.age, 14)

        gigi = test[1]
        self.assertEquals(gigi.name, "Gigi")
        self.assertEquals(gigi.age, None)

    def test_default_value(self):
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="person")
            name = XMLCharField(path="name")
            age = XMLIntegerField(path="age", null=True, default="10")

        xmldata = """<data>
                        <person>
                            <name>Jojo</name>
                            <age>14</age>
                        </person>
                        <person>
                            <name>Gigi</name>
                        </person>
                     </data>"""
        test = TestXMLModel.import_data(xmldata)
        jojo = test[0]
        self.assertEquals(jojo.name, "Jojo")
        self.assertEquals(jojo.age, 14)

        gigi = test[1]
        self.assertEquals(gigi.name, "Gigi")
        self.assertEquals(gigi.age, 10)

    def test_foreign_field(self):
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="person")
            model = XMLForeignKey(MyModel, path="id", null=True)

            class Meta:
                dbModel = MyModelWithForeign

        xmldata = """<data>
                        <person>
                            <id>1</id>
                        </person>
                        <person>
                        </person>

                     </data>"""
        model_object1 = MyModel.objects.create(nom="Gigi", age=10, taille=1.2)
        test = TestXMLModel.import_data(xmldata)
        self.assertEquals(test[0].model, model_object1)
        self.assertEquals(test[1].model, None)

    def test_embed_fields(self):
        class TestInfoXml(XMLModel):
            root = XMLRootField(path="person/info")
            age = XMLIntegerField(path="age")
            taille = XMLFloatField(path="taille")

        class TestXMLModel(XMLModel):
            root = XMLRootField(path="list")
            name = XMLCharField(path="person/name")
            info = XMLEmbed(TestInfoXml)

        xmldata = """<data>
                        <list>
                            <person>
                                <name>Jojo</name>
                                <info>
                                    <age>12</age>
                                    <taille>1.2</taille>
                                </info>
                                <info>
                                    <age>13</age>
                                    <taille>1.3</taille>
                                </info>
                            </person>
                        </list>
                     </data>"""
        test = TestXMLModel.import_data(xmldata)
        self.assertEquals(test[0].name, "Jojo")
        self.assertEquals(test[0].info[1].age, 13)


    def test_foreign_field(self):
        # No exception should be raised
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="person")
            model = XMLForeignKey(MyModel, path="id", null=True, nomatch=True)

            class Meta:
                dbModel = MyModelWithForeign

        xmldata = """<data>
                        <person>
                            <id>1</id>
                        </person>
                        <person>
                            <id>2</id>
                        </person>

                     </data>"""
        model_object1 = MyModel.objects.create(nom="Gigi", age=10, taille=1.2)
        test = TestXMLModel.import_data(xmldata)
        self.assertEquals(test[0].model, model_object1)
        self.assertEquals(test[1].model, None)


    def test_boolean_field(self):
        # No exception should be raised
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="person")
            is_adult = XMLBooleanField(path="adult", is_true=lambda x: x=="yes")

        xmldata = """<data>
                        <person>
                            <adult>yes</adult>
                        </person>
                     </data>"""
        test = TestXMLModel.import_data(xmldata)
        self.assertTrue(test[0].is_adult)

    def test_default_boolean_field(self):
        # No exception should be raised
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="person")
            is_adult = XMLBooleanField(path="adult", is_true=lambda x: x=="yes", null=True, default=False)

        xmldata = """<data>
                        <person>
                        </person>
                     </data>"""
        test = TestXMLModel.import_data(xmldata)
        self.assertEquals(test[0].is_adult, False) # Cannot assert False as None is False

    def test_prepare_xml_data_integer(self):
        def to_int(string):
            if string == "One":
                return "1"
            return string

        xml = "<data><val>One</val></data>"
        int_field = XMLIntegerField(path="val", prepare=to_int, root=None)
        self.assertEquals(int_field.get_prep_value(xml), 1)

    def test_conditional_xpath(self):
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="persons")
            name = XMLCharField(path="person[age<13]/name")

        xmldata = """<data>
                        <persons>
                            <person>
                                <name>Jojo</name>
                                <age>14</age>
                            </person>
                            <person>
                                <name>gigi</name>
                                <age>12</age>
                            </person>
                        </persons>
                     </data>"""
        test = TestXMLModel.import_data(xmldata)
        gigi = test[0]
        self.assertEquals(gigi.name, "gigi")

    def test_multiple_calls(self):
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="persons")
            name = XMLCharField(path="person/name")

        xmldata = """<data>
                        <persons>
                            <person>
                                <name>Jojo</name>
                                <age>14</age>
                            </person>
                            <person>
                                <name>gigi</name>
                                <age>12</age>
                            </person>
                        </persons>
                     </data>"""
        test = TestXMLModel.import_data(xmldata)
        jojo = test[0]
        self.assertEquals(jojo.name, "Jojo")

        test = TestXMLModel.import_data(xmldata)
        jojo = test[0]
        self.assertEquals(jojo.name, "Jojo")




