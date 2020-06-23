from rest_framework import viewsets
from rest_framework import permissions
from rest_framework_api_key.permissions import HasAPIKey

from .serializers import PaperSerializer, RenderSerializer
from .models import Paper, Render


class PaperViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    queryset = Paper.objects.all()
    serializer_class = PaperSerializer


class RenderViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    queryset = Render.objects.all()
    serializer_class = RenderSerializer
