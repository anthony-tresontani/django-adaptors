from datetime import datetime
from adaptor.model import CsvModel
from adaptor.fields import *

class MyCSvModel(CsvModel):
    name = CharField()
    age = IntegerField()
    length = FloatField()

    class Meta:
        delimiter = ";"

def test_performance():
    before = datetime.now()
    data = ['jojo; 12; 1.8']*100000
    for i in range(10):   
       MyCSvModel.import_data(data=data)
    after = datetime.now()
    print after - before

#test_performance()
