from django.urls import reverse
from rest_framework import serializers

from ..models import Slide, Folder


class FolderSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", default=None)
    url = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            "id",
            "name",
            "author",
            "parent",
            "created_at",
            "updated_at",
            "url",
        ]
        read_only_fields = ["author"]

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        parent = attrs.get("parent")
        if parent and not parent.user_can_edit(user):
            errors["parent"] = "You don't have permission to edit this folder."

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)

    def get_url(self, obj):
        return reverse("api:folder-detail", kwargs={"pk": obj.pk})


class SlideSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", default=None)
    thumbnail = serializers.SerializerMethodField()
    associated_image = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    view_url = serializers.SerializerMethodField()

    class Meta:
        model = Slide
        fields = [
            "id",
            "name",
            "information",
            "author",
            "folder",
            "file",
            "image_root",
            "thumbnail",
            "associated_image",
            "metadata",
            "is_public",
            "created_at",
            "updated_at",
            "url",
            "view_url",
        ]
        read_only_fields = ["author", "image_root", "metadata"]

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        folder = attrs.get("folder")
        if folder and not folder.user_can_edit(user):
            errors["folder"] = "You don't have permission to edit this folder."

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)


    def get_thumbnail(self, obj):
        return reverse("api:slide-thumbnail", kwargs={"pk": obj.pk})

    def get_associated_image(self, obj):
        return reverse("api:slide-associated-image", kwargs={"pk": obj.pk})
    def get_url(self, obj):
        return reverse("api:slide-detail", kwargs={"pk": obj.pk})

    def get_view_url(self, obj):
        return reverse("slide_viewer:slide-view", kwargs={"slide_id": obj.pk})
