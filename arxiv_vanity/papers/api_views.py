from rest_framework import viewsets
from rest_framework import permissions
from rest_framework_api_key.permissions import HasAPIKey

from .serializers import PaperSerializer, RenderSerializer
from .models import Paper, Render
from .views import add_paper_cache_control, add_never_cache_headers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404

from .models import Paper, Render, PaperIsNotRenderableError
from .renderer import TooManyRendersRunningError
from ..scraper.arxiv_ids import (
    remove_version_from_arxiv_id,
    ARXIV_URL_RE,
    ARXIV_DOI_RE,
    ARXIV_VANITY_RE,
)
from ..scraper.query import PaperNotFoundError


class PaperViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    queryset = Paper.objects.all()
    serializer_class = PaperSerializer


class RenderViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    queryset = Render.objects.all()
    serializer_class = RenderSerializer

    @action(detail=True, renderer_classes=[TemplateHTMLRenderer])
    def render(self, request, *args, **kwargs):
        force_render = "render" in request.GET
        arxiv_id = "1708.06733"  # kwargs["arxiv_id"]

        arxiv_id, version = remove_version_from_arxiv_id(arxiv_id)
        if version is not None:
            return redirect("paper_detail", arxiv_id=arxiv_id)

        # Get the requested paper
        try:
            paper = Paper.objects.get(arxiv_id=arxiv_id)
        # If it doesn't exist, fetch from arXiv API
        except Paper.DoesNotExist:
            # update_or_create to avoid the race condition where several people
            # hit a new paper at the same time
            try:
                paper, _ = Paper.objects.update_or_create_from_arxiv_id(arxiv_id)
            except PaperNotFoundError:
                raise Http404(f"Paper '{arxiv_id}' not found on arXiv")

        try:
            render_to_display = paper.get_render_to_display_and_render_if_needed(
                force_render=force_render
            )
        except PaperIsNotRenderableError:
            res = Response(
                {"paper": paper},
                template_name="papers/api_paper_detail_not_renderable.html",
                status=404,
            )
            return res  # add_paper_cache_control(res, request)
        except TooManyRendersRunningError:
            res = Response(
                {"paper": paper},
                template_name="papers/api_paper_detail_too_many_renders.html",
                status=503,
            )
            add_never_cache_headers(res)
            return res

        # Switch response based on state
        if render_to_display.state == Render.STATE_RUNNING:
            res = Response(
                {"paper": paper, "render": render_to_display},
                template_name="papers/api_paper_detail_rendering.html",
                status=503,
            )
            add_never_cache_headers(res)
            return res

        elif render_to_display.state == Render.STATE_FAILURE:
            res = Response(
                {"paper": paper},
                template_name="papers/api_paper_detail_error.html",
                status=500,
            )
            return res  # add_paper_cache_control(res, request)

        elif render_to_display.state == Render.STATE_SUCCESS:
            processed_render = render_to_display.get_processed_render()

            res = Response(
                {
                    "paper": paper,
                    "render": render_to_display,
                    "body": processed_render["body"],
                    "links": processed_render["links"],
                    "scripts": processed_render["scripts"],
                    "styles": processed_render["styles"],
                    "abstract": processed_render["abstract"],
                    "first_image": processed_render["first_image"],
                },
                template_name="papers/api_paper_detail.html",
            )
            return res  # add_paper_cache_control(res, request)

        else:
            raise Exception(f"Unknown render state: {render_to_display.state}")
