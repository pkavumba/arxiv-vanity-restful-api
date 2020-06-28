from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField

# Create your models here.
class Annotation(models.Model):
    """
    Annotatorjs http storage fields

    {
        "uri": "http://example.org/",
        "user": "joebloggs",
        "permissions": {
            "read": ["group:__world__"],
            "update": ["joebloggs"],
            "delete": ["joebloggs"],
            "admin": ["joebloggs"],
        },
        "target": [ ... ],
        "text": "This is an annotation I made."
    }
    """

    uri = models.URLField(max_length=50, unique=True)
    user = models.CharField()
    permissions = JSONField()
    target = ArrayField()
    text = models.TextField()

