from django.urls import path

from . import views

app_name = "slide_viewer"

urlpatterns = [
    path("<int:slide_id>/", views.SlideView.as_view(), name="slide_view"),
    path("<int:slide_id>.dzi/", views.get_dzi, name="get_dzi"),
    path(
        "<int:slide_id>_files/<int:level>/<int:col>_<int:row>.<str:tile_format>/",
        views.get_tiles,
        name="get_tiles",
    ),
    path("save_annotation/", views.save_annotation, name="save_annotation"),
]
