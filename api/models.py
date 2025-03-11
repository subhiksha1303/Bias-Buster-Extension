from django.db import models

# Create your models here.
class NewsAnalysis(models.Model):
    original_text = models.TextField()
    unbiased_text = models.TextField()
