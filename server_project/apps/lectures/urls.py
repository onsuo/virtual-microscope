from django.urls import path

from . import views

app_name = "lectures"

urlpatterns = [
    path("", views.LectureListView.as_view(), name="lectures"),
    path("database/", views.LectureDatabaseView.as_view(), name="lecture_database"),
    path("<int:lecture_id>/", views.LectureView.as_view(), name="lecture_view"),
    path(
        "<int:lecture_id>/edit/",
        views.LectureEditView.as_view(),
        name="lecture_edit",
    ),
    path("create/", views.create_lecture, name="create_lecture"),
    path("edit/", views.edit_lecture, name="edit_lecture"),
    path("delete/", views.delete_lecture, name="delete_lecture"),
    path("details/", views.lecture_details, name="lecture_details"),
    path(
        "toggle-activity/",
        views.toggle_lecture_activity,
        name="toggle_lecture_activity",
    ),
]
