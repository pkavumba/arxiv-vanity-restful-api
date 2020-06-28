from rest_framework import viewsets
from rest_framework import permissions
from rest_framework_api_key.permissions import HasAPIKey

from django.template.loader import render_to_string

from .serializers import PaperSerializer, RenderSerializer
from .models import Paper, Render
from .views import add_paper_cache_control, add_never_cache_headers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
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

from rest_framework.exceptions import APIException


class PaperIsNotRenderable(APIException):
    status_code = 404
    default_detail = "paper is unrenderable."
    default_code = "paper_unrenderable"


class PaperRenderFailure(APIException):
    status_code = 503
    default_detail = "paper render failure."
    default_code = "paper_failure"


class TooManyRendersRunning(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable, try again later."
    default_code = "service_unavailable"


class PaperViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    queryset = Paper.objects.all()
    serializer_class = PaperSerializer


class RenderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    queryset = Render.objects.all()
    serializer_class = RenderSerializer

    @action(detail=True, renderer_classes=[JSONRenderer])
    def render(self, request, *args, **kwargs):
        force_render = "render" in request.GET
        arxiv_id = request.query_params.get(
            "arxiv_id", "1708.06733"
        )  # kwargs["arxiv_id"]

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
            rendered = render_to_string(
                "papers/api_paper_detail_not_renderable.html", {"paper": paper}
            )
            # res = raise(rendered)
            raise PaperIsNotRenderable(
                rendered
            )  # add_paper_cache_control(res, request)
        except TooManyRendersRunningError:
            rendered = render_to_string(
                "papers/api_paper_detail_too_many_renders.html", {"paper": paper}
            )
            raise TooManyRendersRunning(rendered)  # res

        # Switch response based on state
        if render_to_display.state == Render.STATE_RUNNING:
            rendered = render_to_string(
                "papers/api_paper_detail_rendering.html",
                {"paper": paper, "render": render_to_display},
            )
            return Response(
                {
                    "render_state": render_to_display.state,
                    "paper": PaperSerializer(paper, context={"request": request}).data,
                }
            )

        elif render_to_display.state == Render.STATE_FAILURE:
            rendered = render_to_string(
                "papers/api_paper_detail_error.html", {"paper": paper}
            )
            raise PaperRenderFailure(rendered)  # return Response({"data": rendered})

        elif render_to_display.state == Render.STATE_SUCCESS:
            processed_render = render_to_display.get_processed_render()
            rendered = render_to_string(
                "papers/api_paper_detail.html",
                {
                    "paper": paper,
                    "render_state": render_to_display.state,
                    "body": processed_render["body"],
                    "links": processed_render["links"],
                    "scripts": processed_render["scripts"],
                    "styles": processed_render["styles"],
                    "abstract": processed_render["abstract"],
                    "first_image": processed_render["first_image"],
                },
            )

            return Response(
                {
                    "paper": PaperSerializer(paper, context={"request": request}).data,
                    "render_state": render_to_display.state,
                    "body": processed_render["body"],
                    "links": processed_render["links"],
                    "scripts": processed_render["scripts"],
                    "styles": processed_render["styles"],
                    "abstract": processed_render["abstract"],
                    "first_image": processed_render["first_image"],
                    "rendered": rendered,
                }
            )

        else:
            raise Exception(f"Unknown render state: {render_to_display.state}")
