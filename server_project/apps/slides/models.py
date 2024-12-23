import os
import shutil

from django.conf import settings
from django.db import models
from openslide import OpenSlide
from openslide.deepzoom import DeepZoomGenerator


class SlideManager(models.Manager):
    def check_integrity_all(self):
        """Check integrity of all slides and return problematic ones"""
        problematic_slides = []
        for slide in self.all():
            if not slide.check_integrity():
                problematic_slides.append(slide)
        return problematic_slides

    def get_recent_slides(self, days=7):
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)

    def get_by_department(self, department_name):
        return self.filter(department__name=department_name)


class Slide(models.Model):
    id = models.AutoField(primary_key=True)
    file = models.FileField(
        upload_to="slides/",
        help_text="Choose a slide file to upload.",
    )
    name = models.CharField(
        max_length=250,
        unique=True,
        help_text="Name of the slide.",
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Unique slug for the slide.",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the slide.",
    )
    image_path = models.CharField(
        max_length=250,
        blank=True,
        help_text="Path to the image files.",
    )
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column="uploaded_by",
        related_name="slides",
        blank=True,
        null=True,
    )
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        related_name="slides",
        blank=True,
        null=True,
    )

    objects = SlideManager()

    class Meta:
        verbose_name = "Slide"
        verbose_name_plural = "Slides"
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, skip_processing=False, **kwargs):
        """Handle save with all related operations"""
        try:
            # Handle file changes for existing instances
            if self.pk:
                old_instance = Slide.objects.get(pk=self.pk)
                self.handle_file_update(old_instance)

            # Regular save
            self.image_path = os.path.join("images", self.slug)
            super().save(*args, **kwargs)

            # Process slide after save
            if not skip_processing:
                self.process_slide()

        except Exception as e:
            # Clean up any partial changes
            self._cleanup_on_error(os.path.join(settings.MEDIA_ROOT, self.image_path))
            raise Exception(f"Failed to save slide: {str(e)}")

    def delete(self, *args, **kwargs):
        """Handle delete with cleanup"""
        try:
            self.delete_files()
            super().delete(*args, **kwargs)
        except Exception as e:
            raise Exception(f"Failed to delete slide: {str(e)}")

    def process_slide(self):
        """Combine generation of tiles and metadata"""
        slideimage_dir = os.path.join(settings.MEDIA_ROOT, self.image_path)

        try:
            with OpenSlide(self.file.path) as slide:
                if not os.path.exists(slideimage_dir):
                    self._generate_image_files(slide, slideimage_dir)

                if not self.metadata:
                    self._save_metadata(slide)
        except Exception as e:
            self._cleanup_on_error(slideimage_dir)
            raise Exception(f"Failed to process slide {self.slug}: {str(e)}")

    def delete_files(self):
        """Delete all associated files"""
        # delete slide file
        self.file.delete(False)
        # delete image files directory
        slideimage_dir = os.path.join(settings.MEDIA_ROOT, self.image_path)
        if os.path.exists(slideimage_dir):
            shutil.rmtree(slideimage_dir)

    def handle_file_update(self, old_instance):
        """Handle file and directory updates when file or slug changes"""
        old_slideimage_dir = os.path.join(settings.MEDIA_ROOT, old_instance.image_path)

        if old_instance.file != self.file:
            # delete old files
            old_instance.file.delete(False)
            shutil.rmtree(old_slideimage_dir)
        elif old_instance.slug != self.slug:
            if os.path.exists(old_slideimage_dir):
                # rename existing directory
                slideimage_dir = os.path.join(settings.MEDIA_ROOT, self.image_path)
                os.rename(old_slideimage_dir, slideimage_dir)

    def check_integrity(self) -> dict:
        """Check integrity of the slide's files and metadata"""
        status = {
            "file_exists": False,
            "dzi_exists": False,
            "tiles_complete": False,
            "metadata_valid": False,
            "needs_repair": False,
        }

        # Check original file
        status["file_exists"] = os.path.exists(self.file.path)

        # Check DZI and tiles
        slideimage_dir = os.path.join(settings.MEDIA_ROOT, self.image_path)
        dzi_path = os.path.join(slideimage_dir, "image.dzi")
        status["dzi_exists"] = os.path.exists(dzi_path)

        if status["dzi_exists"] and status["file_exists"]:
            try:
                with OpenSlide(self.file.path) as slide:
                    deepzoom = DeepZoomGenerator(slide)
                    status["tiles_complete"] = self._verify_tiles(deepzoom, slideimage_dir)
            except Exception:
                status["tiles_complete"] = False

        status["metadata_valid"] = self._verify_metadata()
        status["needs_repair"] = not all(
            [
                status["file_exists"],
                status["dzi_exists"],
                status["tiles_complete"],
                status["metadata_valid"],
            ]
        )

        return status

    def repair(self) -> dict:
        """Repair any missing or corrupted components"""
        status = self.check_integrity()

        if not status["needs_repair"]:
            return status

        try:
            with OpenSlide(self.file.path) as slide:
                slideimage_dir = os.path.join(settings.MEDIA_ROOT, self.image_path)

                if not (status["dzi_exists"] and status["tiles_complete"]):
                    if os.path.exists(slideimage_dir):
                        shutil.rmtree(slideimage_dir)
                    self._generate_image_files(slide, slideimage_dir)

                if not status["metadata_valid"]:
                    self._save_metadata(slide)

            return self.check_integrity()

        except Exception as e:
            raise Exception(f"Failed to repair slide {self.slug}: {str(e)}")

    def _generate_image_files(self, slide: OpenSlide, slideimage_dir):
        """Generate related images for the slide"""
        FORMAT = "jpeg"
        try:
            # Setup directories
            dzi_path = os.path.join(slideimage_dir, "image.dzi")
            tile_dir = os.path.join(slideimage_dir, "image_files")
            os.makedirs(tile_dir, exist_ok=True)

            # Initialize DeepZoom
            deepzoom = DeepZoomGenerator(slide)

            # Create DZI file
            dzi = deepzoom.get_dzi(FORMAT)
            with open(dzi_path, "w") as f:
                f.write(dzi)

            # Generate tiles
            for level in range(deepzoom.level_count):
                level_dir = os.path.join(tile_dir, str(level))
                os.makedirs(level_dir, exist_ok=True)

                cols, rows = deepzoom.level_tiles[level]
                for col in range(cols):
                    for row in range(rows):
                        tile_path = os.path.join(level_dir, f"{col}_{row}.{FORMAT}")
                        tile = deepzoom.get_tile(level, (col, row))
                        tile.save(tile_path)

            # Save thumbnail and associated image
            slide.get_thumbnail((256, 256)).save(os.path.join(slideimage_dir, "thumbnail.png"))
            slide.associated_images.get("macro").save(
                os.path.join(slideimage_dir, "associated.png")
            )

        except Exception as e:
            self._cleanup_on_error(slideimage_dir)
            raise Exception(f"Failed to generate tiles: {str(e)}")

    def _save_metadata(self, slide):
        """Extract and save metadata from the slide"""
        try:
            full_metadata = slide.properties
            metadata = {
                "mpp-x": float(full_metadata.get("openslide.mpp-x")),
                "mpp-y": float(full_metadata.get("openslide.mpp-y")),
                "sourceLens": int(full_metadata.get("hamamatsu.SourceLens")),
                "created": full_metadata.get("hamamatsu.Created"),
            }
            Slide.objects.filter(pk=self.pk).update(metadata=metadata)
            self.metadata = metadata  # Update instance attribute
        except Exception as e:
            raise Exception(f"Failed to save metadata: {str(e)}")

    def _verify_tiles(self, deepzoom, slideimage_dir):
        """Verify all expected tiles exist"""
        tile_dir = os.path.join(slideimage_dir, "image_files")

        for level in range(deepzoom.level_count):
            level_dir = os.path.join(tile_dir, str(level))
            if not os.path.exists(level_dir):
                return False

            cols, rows = deepzoom.level_tiles[level]
            for col in range(cols):
                for row in range(rows):
                    tile_path = os.path.join(level_dir, f"{col}_{row}.jpeg")
                    if not os.path.exists(tile_path):
                        return False
        return True

    def _verify_metadata(self):
        """Verify metadata is complete"""
        required_fields = ["mpp-x", "mpp-y", "sourceLens", "created"]
        if not self.metadata:
            return False
        return all(field in self.metadata for field in required_fields)

    @staticmethod
    def _cleanup_on_error(directory):
        """Clean up files if an error occurs during processing"""
        if os.path.exists(directory):
            try:
                shutil.rmtree(directory)
            except Exception:
                pass


class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    slides = models.ManyToManyField(
        "Slide",
        related_name="tags",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ("name",)

    def __str__(self):
        return self.name
