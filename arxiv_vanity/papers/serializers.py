from rest_framework import serializers

from .models import Paper, Render


class PaperSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Paper
        exclude = ["source_file", "is_deleted"]


class RenderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Render
        exclude = ["container_inspect", "container_logs", "container_id"]
