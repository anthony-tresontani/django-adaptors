from decimal import Decimal

from django.test import TestCase
from adaptor.fields import *
from adaptor.model import XMLModel
from adaptor import exceptions
from tests.test_app.models import *


class TestXMLImporter(TestCase):

    def test_extract_xml_data_simplest_case(self):
        xml = "<name>jojo</name>"
        field = XMLCharField(path="/name", root=None)
        self.assertEquals(field.get_prep_value(xml), "jojo")

    def test_extract_xml_data_from_attribute(self):
        xml = "<person name='jojo'>jojotext</person>"
        field = XMLCharField(path="/person", attribute="name", root=None)
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

    def test_extract_xml_data_decimal(self):
        xml = "<data><name>jojo</name><length>2.0</length></data>"
        decimal_field = XMLDecimalField(path="length", root=None)
        self.assertEquals(decimal_field.get_prep_value(xml), Decimal('2.0'))

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
        self.assertRaises(exceptions.FieldValueMissing, TestXMLModel.import_data, xmldata)


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
            model = XMLDjangoModelField(MyModel, path="id", null=True)

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

    def test_element_values_can_be_transformed(self):
        class TestXMLDoc(XMLModel):
            root = XMLRootField(path="/person")
            name = XMLCharField(path="/person/name")

            def transform_name(self, value):
                return value.upper()

        xml = """<?xml version="1.0" encoding="UTF-8" ?>
                 <person>
                     <name>barry</name>
                 </person>"""
        doc = TestXMLDoc.import_data(xml)[0]
        self.assertEqual('BARRY', doc.as_dict()['name'])

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
            model = XMLDjangoModelField(MyModel, path="id", null=True, nomatch=True)

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
                        <person> </person>
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

    def test_get_data_fields(self):
        class TestXMLModel(XMLModel):
            root = XMLRootField(path="persons")
            name = XMLCharField(path="person/name")

        self.assertEquals(TestXMLModel.get_data_fields(), ['name'])

    def test_as_dict(self):
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
        self.assertEquals(jojo.as_dict(), {"name":"Jojo"})

    def test_choices(self):
        xml_valid = "<data><choice>Y</choice></data>"
        xml_invalid = "<data><choice>y</choice></data>"
        choice_field= XMLCharField(path="choice", choices=['Y', 'N'])
        self.assertEquals(choice_field.get_prep_value(xml_valid), 'Y')
        with self.assertRaises(ValueError):
            self.assertEquals(choice_field.get_prep_value(xml_invalid), None)

    def test_transform_method(self):
         class TestXMLModel(XMLModel):
            root = XMLRootField(path="persons")
            name = XMLCharField(path="person/name")

            def transform_name(self, name):
                return "transformed"

         xmldata = """<data>
                        <persons>
                            <person>
                                <name>Jojo</name>
                                <age>14</age>
                            </person>
                        </persons>
                     </data>"""

         test = TestXMLModel.import_data(xmldata)
         jojo = test[0]
         self.assertEquals(jojo.name, "transformed")

    def test_errors(self):
        class TestXMLModel(XMLModel):
            root = XMLRootField(path=".")
            value = XMLIntegerField(path="value")

            class Meta:
                raise_exception = False

        xmldata_valid = """<person>
                            <value>12</value>
                      </person>
                  """
        test = TestXMLModel.import_data(xmldata_valid)
        self.assertEquals(len(test[0].errors), 0)

        xmldata_invalid = """<person>
                            <value>twelve</value>
                      </person>
                  """
        test = TestXMLModel.import_data(xmldata_invalid)
        self.assertEquals(len(test[0].errors), 1)
        print test[0].errors
        assert False


    def test_embed_transformation(self):
        class TestInfoXml(XMLModel):
            root = XMLRootField(path="person/info")
            age = XMLIntegerField(path="age")
            taille = XMLFloatField(path="taille")

        class TestXMLModel(XMLModel):
            root = XMLRootField(path="list")
            name = XMLCharField(path="person/name")
            info = XMLEmbed(TestInfoXml)

            def transform_info(self, infos):
                return filter(lambda info: info.age == 12, infos)

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
        self.assertEquals(len(test[0].info), 1)
