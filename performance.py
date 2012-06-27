from datetime import datetime
from adaptor.model import CsvModel
from adaptor.fields import *

class MyCSvModel(CsvModel):
    name = CharField()
    age = IntegerField()
    length = FloatField()

    class Meta:
        delimiter = ";"

def test_performance(row=100000, cycle=10):
    before = datetime.now()
    data = ['jojo; 12; 1.8']*row
    for i in range(cycle):   
       MyCSvModel.import_data(data=data)
    after = datetime.now()
    print after - before
