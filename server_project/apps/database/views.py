import json
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView

from .models import Folder, Slide


class DatabaseView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "database/database.html"
    context_object_name = "items"
    permission_required = ["database.view_folder", "database.view_slide"]

    def get_folder(self):
        folder_id = self.request.GET.get("folder")
        if not folder_id:
            return None
        return get_object_or_404(Folder, id=folder_id)

    def get_queryset(self):
        current = self.get_folder()

        if current:
            subfolders = current.subfolders.all()
        else:
            subfolders = Folder.objects.base_folders()

        slides = Slide.objects.viewable_by_folder(self.request.user ,current)

        for folder in subfolders:
            folder.type = "folder"

        for slide in slides:
            slide.type = "slide"

        items = list(subfolders) + list(slides)
        return sorted(items, key=lambda x: (x.type, x.name.lower()))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current = self.get_folder()

        context["current_folder"] = current
        context["breadcrumbs"] = self._generate_breadcrumbs(current)
        context["editable"] = (
            current.user_can_edit(self.request.user)
            if current
            else self.request.user.is_admin()
        )
        return context

    def _generate_breadcrumbs(self, folder):
        breadcrumbs = []
        current = folder

        while current:
            breadcrumbs.append({"id": current.id, "name": current.name})
            current = current.parent
        breadcrumbs.append({"id": "", "name": "Root"})

        breadcrumbs.reverse()
        return breadcrumbs


@login_required
@permission_required("database.add_folder")
def create_folder(request):
    if request.method == "POST":
        name = request.POST.get("name")
        parent_id = request.POST.get("parent_id")

        try:
            if parent_id:
                parent = Folder.objects.get(id=parent_id)
                if parent.user_can_edit(request.user):
                    Folder.objects.create(name=name, parent=parent, author=request.user)
                    messages.success(request, f'Folder "{name}" created successfully.')
                else:
                    messages.error(
                        request, "You don't have permission to create folder here."
                    )
            else:
                messages.error(request, "You can't create folder here.")
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                messages.warning(
                    request, f'Folder "{name}" already exists. Try another name.'
                )
            else:
                messages.error(request, f"Failed to create folder: {str(e)}")

        # Redirect back to the same page with the current folder
        return redirect(request.META.get("HTTP_REFERER", "database:slide_navigation"))


@login_required
@permission_required("database.change_folder")
def rename_folder(request):
    if request.method == "POST":
        folder_id = request.POST.get("folder_id")
        new_name = request.POST.get("new_name")

        try:
            folder = Folder.objects.get(id=folder_id)
            if folder.user_can_edit(request.user) and not folder.is_base_folder():
                folder.name = new_name
                folder.save()
                messages.success(
                    request, f'Folder renamed to "{new_name}" successfully.'
                )
            else:
                messages.error(
                    request, "You don't have permission to rename this folder."
                )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                messages.warning(
                    request, f'Folder "{new_name}" already exists. Try another name.'
                )
            else:
                messages.error(request, f"Failed to rename folder: {str(e)}")

        # Redirect back to the same page with the current folder
        return redirect(request.META.get("HTTP_REFERER", "database:slide_navigation"))


@login_required
@permission_required("database.change_folder")
def move_folder(request):
    if request.method == "POST":
        folder_id = request.POST.get("folder_id")
        new_parent_id = request.POST.get("destination_folder_id")

        try:
            folder = Folder.objects.get(id=folder_id)
            new_parent = Folder.objects.get(id=new_parent_id)

            if (
                folder.user_can_edit(request.user)
                and new_parent.user_can_edit(request.user)
                and not folder.is_base_folder()
            ):
                if not folder.is_children(new_parent) and not folder == new_parent:
                    folder.parent = new_parent
                    folder.save()
                    messages.success(
                        request,
                        f'Folder "{folder.name}" moved to "{new_parent.get_full_path()}" successfully.',
                    )
                else:
                    messages.error(
                        request, "You can't move a folder to its own subfolder."
                    )
            else:
                messages.error(
                    request, "You don't have permission to move this folder."
                )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                messages.warning(
                    request, f'Folder "{folder.name}" already exists at this location.'
                )
            else:
                messages.error(request, f"Failed to move folder: {str(e)}")

        # Redirect back to the same page with the current folder
        return redirect(request.META.get("HTTP_REFERER", "database:slide_navigation"))


@login_required
@permission_required("database.delete_folder")
def delete_folder(request):
    if request.method == "POST":
        folder_id = request.POST.get("folder_id")

        try:
            folder = Folder.objects.get(id=folder_id)
            if folder.user_can_edit(request.user) and not folder.is_base_folder():
                if folder.is_empty():
                    folder.delete()
                    messages.success(
                        request, f'Folder "{folder.name}" deleted successfully.'
                    )
                else:
                    messages.warning(
                        request,
                        f'Folder "{folder.name}" is not empty. Please delete its contents first.',
                    )
            else:
                messages.error(
                    request, "You don't have permission to delete this folder."
                )
        except Exception as e:
            messages.error(request, f"Failed to delete folder: {str(e)}")

        # Redirect back to the same page with the current folder
        return redirect(request.META.get("HTTP_REFERER", "database:slide_navigation"))


@login_required
@permission_required("database.view_folder")
def folder_details(request):
    if request.method == "POST":
        data = json.loads(request.body)
        folder_id = data.get("folder_id")

        try:
            folder = Folder.objects.get(id=folder_id)
            data = {
                "name": folder.name,
                "created_at": timezone.localtime(folder.created_at).strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "updated_at": timezone.localtime(folder.updated_at).strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "author": folder.author.username or "-",
                "subfolder_count": folder.subfolders.all().count(),
                "slide_count": folder.slides.all().count(),
            }
            return JsonResponse(data)
        except Folder.DoesNotExist:
            return JsonResponse({"error": "Folder not found"}, status=404)


@login_required
@permission_required("database.add_slide")
def upload_slide(request):
    if request.method == "POST":
        file = request.FILES.get("slideFile")
        folder_id = request.POST.get("folder_id")
        slide_name = request.POST.get("slide_name")
        slide_information = request.POST.get("slide_information")
        is_public = request.POST.get("is_public") == "true"

        try:
            if file:
                if not folder_id and request.user.is_admin():
                    Slide.objects.create(
                        file=file,
                        name=slide_name,
                        information=slide_information,
                        author=request.user,
                        is_public=is_public,
                    )
                    messages.success(
                        request, f'Slide "{file.name}" uploaded to "Root" successfully.'
                    )
                else:
                    folder = Folder.objects.get(id=folder_id)
                    if folder.user_can_edit(request.user):
                        Slide.objects.create(
                            file=file,
                            name=slide_name,
                            information=slide_information,
                            author=request.user,
                            folder=folder,
                            is_public=is_public,
                        )
                        messages.success(
                            request,
                            f'Slide "{file.name}" uploaded to "{folder.get_full_path()}" successfully.',
                        )
                    else:
                        messages.error(
                            request, "You don't have permission to upload here."
                        )
            else:
                messages.error(request, "No file selected.")
        except Exception as e:
            messages.error(request, f"Failed to upload slide: {str(e)}")

        # Redirect back to the same page with the current folder
        return redirect(request.META.get("HTTP_REFERER", "database:slide_navigation"))


@login_required
@permission_required("database.change_slide")
def edit_slide(request):
    if request.method == "POST":
        slide_id = request.POST.get("slide_id")
        new_name = request.POST.get("new_name")
        new_information = request.POST.get("new_information")
        new_is_public = request.POST.get("new_is_public") == "true"

        try:
            slide = Slide.objects.get(id=slide_id)
            if slide.user_can_edit(request.user):
                slide.name = new_name
                slide.information = new_information
                slide.is_public = new_is_public
                slide.save()
                messages.success(request, f'Slide "{slide.name}" updated successfully.')
            else:
                messages.error(request, "You don't have permission to edit this slide.")
        except Exception as e:
            messages.error(request, f"Failed to update slide: {str(e)}")

        # Redirect back to the same page with the current folder
        return redirect(request.META.get("HTTP_REFERER", "database:slide_navigation"))


@login_required
@permission_required("database.change_slide")
def move_slide(request):
    if request.method == "POST":
        slide_id = request.POST.get("slide_id")
        new_folder_id = request.POST.get("destination_folder_id")

        try:
            slide = Slide.objects.get(id=slide_id)
            if new_folder_id:
                new_folder = Folder.objects.get(id=new_folder_id)
                if slide.user_can_edit(request.user) and new_folder.user_can_edit(
                    request.user
                ):
                    slide.folder = new_folder
                    slide.save()
                    messages.success(
                        request,
                        f'Slide "{slide.name}" moved to "{new_folder.get_full_path()}" successfully.',
                    )
                else:
                    messages.error(
                        request, "You don't have permission to move this slide."
                    )
            else:
                if request.user.is_admin():
                    slide.folder = None
                    slide.save()
                    messages.success(
                        request, f'Slide "{slide.name}" moved to "Root" successfully.'
                    )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                messages.warning(
                    request, f'Slide "{slide.name}" already exists at this location.'
                )
            else:
                messages.error(request, f"Failed to move slide: {str(e)}")

        # Redirect back to the same page with the current folder
        return redirect(request.META.get("HTTP_REFERER", "database:slide_navigation"))


@login_required
@permission_required("database.delete_slide")
def delete_slide(request):
    if request.method == "POST":
        slide_id = request.POST.get("slide_id")

        try:
            slide = Slide.objects.get(id=slide_id)
            if slide.user_can_edit(request.user):
                slide.delete()
                messages.success(request, f'Slide "{slide.name}" deleted successfully.')
            else:
                messages.error(
                    request, "You don't have permission to delete this slide."
                )
        except Exception as e:
            messages.error(request, f"Failed to delete slide: {str(e)}")

        # Redirect back to the same page with the current folder
        return redirect(request.META.get("HTTP_REFERER", "database:slide_navigation"))


@login_required
@permission_required("database.view_slide")
def slide_details(request):
    if request.method == "POST":
        data = json.loads(request.body)
        slide_id = data.get("slide_id")

        try:
            slide = Slide.objects.get(id=slide_id)
            if slide.user_can_view(request.user):
                data = {
                    "id": slide.id,
                    "name": slide.name,
                    "information": slide.information,
                    "created_at": slide.created_at.strftime("%Y-%m-%d %H:%M"),
                    "updated_at": slide.updated_at.strftime("%Y-%m-%d %H:%M"),
                    "author": slide.author.username,
                    "folder": slide.folder.get_full_path() or "Root",
                    "metadata": slide.metadata,
                    "file": slide.file.name,
                    "is_public": slide.is_public,
                }
                return JsonResponse(data)
            else:
                return JsonResponse({"error": "Permission denied"}, status=403)
        except Slide.DoesNotExist:
            return JsonResponse({"error": "Slide not found"}, status=404)


@login_required
@permission_required("database.view_folder")
def get_folder_tree(request):
    def _build_tree(folder):
        return {
            "id": folder.id,
            "name": folder.name,
            "subfolders": [
                _build_tree(subfolders) for subfolders in folder.subfolders.all()
            ],
        }

    if request.user.is_admin():
        base_folders = Folder.objects.filter(parent=None)
        tree = [_build_tree(folder) for folder in base_folders]
    else:
        base_folders = Folder.objects.editable_base_folders(request.user)
        tree = [_build_tree(folder) for folder in base_folders]

    data = {
        "tree": tree,
        "show_root": request.user.is_admin(),
    }

    return JsonResponse(data, safe=False)


@login_required
@permission_required("database.view_folder")
def get_folder_items(request):
    if request.method == "POST":
        folder_id = request.POST.get("folder-id")
        folder = Folder.objects.get(id=folder_id)

        subfolders = folder.subfolders.all()
        slides = Slide.objects.viewable_by_folder(request.user, folder, )

        data = {
            "subfolders": [{"id": f.id, "name": f.name} for f in subfolders],
            "database": [{"id": s.id, "name": s.name} for s in slides],
        }
        return JsonResponse(data)


@login_required
@permission_required(["database.view_slide", "slide_viewer.view_annotation"])
def get_slide_annotations(request):
    if request.method == "POST":
        slide_id = request.POST.get("slide-id")
        slide = Slide.objects.get(id=slide_id)

        data = {"annotations": []}
        for annotation in slide.annotations.all():
            data["annotations"].append(
                {
                    "id": annotation.id,
                    "name": annotation.name,
                    "author": annotation.author.username,
                }
            )

        return JsonResponse(data)


def get_thumbnail(request, slide_id):
    """Serve the thumbnail image for a slide."""

    thumbnail_path = get_object_or_404(Slide, id=slide_id).get_thumbnail_path()

    try:
        with open(thumbnail_path, "rb") as f:
            thumbnail = BytesIO(f.read())
        return HttpResponse(thumbnail, content_type="image/png")
    except Exception as e:
        messages.error(request, f"Failed to load thumbnail: {str(e)}")


def get_associated_image(request, slide_id):
    """Serve the associated image for a slide."""

    associated_image_path = get_object_or_404(
        Slide, id=slide_id
    ).get_associated_image_path()

    try:
        with open(associated_image_path, "rb") as f:
            associated_image = BytesIO(f.read())
        return HttpResponse(associated_image, content_type="image/png")
    except Exception as e:
        messages.error(request, f"Failed to load associated image: {str(e)}")
