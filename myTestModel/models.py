from django.db import models

# Create your models here.
class MyModel(models.Model):

    nom = models.CharField(max_length=15)
    age = models.IntegerField()
    taille = models.FloatField()
