from django.conf import settings
from django.db import models


class Annotation(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=True)
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the annotation",
    )
    data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="created_by",
        on_delete=models.CASCADE,
        related_name="annotations",
        blank=True,
        null=True,
    )
    slide = models.ForeignKey(
        "database.Slide",
        on_delete=models.CASCADE,
        related_name="annotations",
    )

    class Meta:
        unique_together = ("name", "author", "slide")
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.name} - {self.author} - {self.slide}"

    def user_can_edit(self, user):
        if user.is_admin():
            return True
        return self.author == user

    def user_can_view(self, user):
        return self.user_can_edit(user) or self.slide.user_can_view()