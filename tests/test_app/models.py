from django.db import models

# Create your models here.
class MyModel(models.Model):
    nom = models.CharField(max_length=15)
    age = models.IntegerField()
    taille = models.FloatField()
    
class MyModel2(models.Model):
    other_pk = models.PositiveSmallIntegerField()
    
class MyModelWithForeign(models.Model):
    foreign = models.ForeignKey(MyModel, on_delete=models.CASCADE)
    
class OtherForeign(models.Model):
    foreign = models.ForeignKey(MyModel, on_delete=models.CASCADE)
    
class MultipleModel(models.Model):
    nom = models.CharField(max_length=100)
    note = models.IntegerField()
    
class ComposedKeyForeign(models.Model):
    key_1 = models.PositiveIntegerField()
    key_2 = models.PositiveIntegerField()

class ComposedKey(models.Model):
    composed_key_foreign = models.ForeignKey(ComposedKeyForeign, on_delete=models.CASCADE)
    
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

class MyDualModel(models.Model): 
    text_1 = models.CharField(max_length=10)
    text_2 = models.CharField(max_length=10)   

class FirstNameModel(models.Model):
    first_name = models.CharField(max_length=10)
    
class LastNameModel(models.Model):
    last_name = models.CharField(max_length=10)
    
class LastNameModelWithForeign(models.Model):
    foreign = models.ForeignKey(FirstNameModel, on_delete=models.CASCADE)
    last_name = models.CharField(max_length=10)