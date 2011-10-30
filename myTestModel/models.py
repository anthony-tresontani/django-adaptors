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
    
class ComposedKeyForeign(models.Model):
    
    key_1 = models.PositiveIntegerField()
    key_2 = models.PositiveIntegerField()

class ComposedKey(models.Model):
    
    composed_key_foreign = models.ForeignKey(ComposedKeyForeign)
    
class MyModelBis(models.Model):

    nom = models.CharField(max_length=15)
    age = models.IntegerField()
    taille = models.FloatField()
    poids = models.FloatField()

class MyModelTer(models.Model):

    nom = models.CharField(max_length=15)
    age = models.IntegerField()
    taille = models.FloatField()
    poids = models.FloatField()
    bool = models.BooleanField()

    