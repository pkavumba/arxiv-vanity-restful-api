from rest_framework import serializers

from .models import Paper


class PaperSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Paper
        exclude = ["source_file", "is_deleted"]

