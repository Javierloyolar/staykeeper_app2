from django.db import models

class Guest(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    
    def __str__(self):
        return self.full_name