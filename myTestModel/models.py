from django.db import models

# Create your models here.
class MyModel(models.Model):

    nom = models.CharField(max_length=15)
    age = models.IntegerField()
    taille = models.FloatField()
    
class MyModel2(models.Model):

    other_pk = models.PositiveSmallIntegerField()
    
class MyModelWithForeign(models.Model):
    
    foreign = models.ForeignKey(MyModel)
    
class OtherForeign(models.Model):
    
    foreign = models.ForeignKey(MyModel)
    
class MultipleModel(models.Model):
    
    nom = models.CharField(max_length=100)
    note = models.IntegerField()
