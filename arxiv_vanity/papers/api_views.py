from rest_framework import viewsets
from rest_framework import permissions
from rest_framework_api_key.permissions import HasAPIKey

from .serializers import PaperSerializer
from .models import Paper


class PaperViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    queryset = Paper.objects.all()
    serializer_class = PaperSerializer
