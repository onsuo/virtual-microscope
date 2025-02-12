import json
import os
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from apps.database.models import Slide
from apps.slide_viewer.models import Annotation


class SlideView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Render a page with the OpenSeadragon viewer for the specified slide."""

    template_name = "slide_viewer/viewer.html"
    permission_required = "database.view_slide"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slide_id = kwargs.get("slide_id")
        annotation_id = self.request.GET.get("annotation")

        slide = get_object_or_404(Slide, id=slide_id)
        try:
            annotation = Annotation.objects.get(id=annotation_id)
            if annotation.slide != slide:
                raise Annotation.DoesNotExist
        except Annotation.DoesNotExist or AttributeError:
            annotation = None

        context["slide"] = slide
        context["dzi_url"] = reverse_lazy(
            "slide_viewer:get_dzi", kwargs={"slide_id": slide_id}
        )
        context["annotation"] = json.dumps(annotation.data) if annotation else "{}"
        context["editable"] = slide.user_can_edit(self.request.user)
        return context


def get_dzi(request, slide_id):
    """Serve the Deep Zoom Image (DZI) XML file for a slide."""

    dzi_path = get_object_or_404(Slide, id=slide_id).get_dzi_path()

    try:
        with open(dzi_path, "r") as f:
            dzi_content = f.read()
        return HttpResponse(dzi_content, content_type="application/xml")
    except Exception as e:
        messages.error(request, f"Failed to load DZI file: {str(e)}")


def get_tiles(request, slide_id, level, col, row, tile_format):
    """Serve individual Deep Zoom tiles for a slide."""

    if tile_format not in ["jpeg", "png"]:
        messages.error(request, "Unsupported format")

    tile_directory = get_object_or_404(Slide, id=slide_id).get_tile_directory()

    try:
        with open(
            os.path.join(tile_directory, str(level), f"{col}_{row}.{tile_format}"), "rb"
        ) as f:
            tile = BytesIO(f.read())
        return HttpResponse(tile, content_type=f"image/{tile_format}")
    except Exception as e:
        messages.error(request, f"Failed to load tile images: {str(e)}")


def save_annotation(request, slide_id):
    """Save an annotation for a slide."""

    slide = get_object_or_404(Slide, id=slide_id)

    if request.method == "POST":
        annotation_id = request.POST.get("annotationId")
        name = request.POST.get("name")
        description = request.POST.get("description")
        data = json.loads(request.POST.get("data", "[]"))

        if annotation_id:
            try:
                annotation = Annotation.objects.get(id=annotation_id)
                if annotation.user_can_edit(request.user):
                    annotation.name = name
                    annotation.description = description
                    annotation.data = data
                    annotation.save()
                    return HttpResponse(f'Annotation "{name}" updated successfully.')
                else:
                    return HttpResponse("You are not allowed to edit this annotation.")
            except Annotation.DoesNotExist or AttributeError:
                return HttpResponse("Annotation not found.")
        else:
            Annotation.objects.create(
                name=name,
                description=description,
                data=data,
                author=request.user,
                slide=slide,
            )
            return HttpResponse(f'Annotation "{name}" created successfully.')
