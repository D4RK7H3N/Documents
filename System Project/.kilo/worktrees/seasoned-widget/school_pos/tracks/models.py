from django.db import models


class Track(models.Model):
    """Main academic track (e.g., Academic Track, TVL Track)"""

    LEVEL_TYPE_CHOICES = [
        ("SHS", "Senior High School"),
        ("COL", "College"),
        ("BUN", "Bundled"),
        ("ALL", "All Levels"),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    level_type = models.CharField(
        max_length=3,
        choices=LEVEL_TYPE_CHOICES,
        default="SHS",
        help_text="Which level type this track applies to",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tracks"
        ordering = ["name"]
        verbose_name = "Track"
        verbose_name_plural = "Tracks"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Strand(models.Model):
    """Academic strand under a track (e.g., STEM, ABM, HUMSS under Academic Track)"""

    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="strands")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "strands"
        ordering = ["track", "name"]
        verbose_name = "Strand"
        verbose_name_plural = "Strands"
        unique_together = ["track", "code"]

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.track.name}"

    @property
    def full_name(self):
        """Returns track and strand name combined"""
        return f"{self.track.name} - {self.name}"


class Course(models.Model):
    """College or Bundled course (e.g., BS Computer Science, BSBA)"""

    LEVEL_TYPE_CHOICES = [
        ("COL", "College"),
        ("BUN", "Bundled"),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    abbreviation = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    level_type = models.CharField(
        max_length=3,
        choices=LEVEL_TYPE_CHOICES,
        default="COL",
        help_text="Course level type (College or Bundled)",
    )
    duration_years = models.PositiveSmallIntegerField(default=4)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "courses"
        ordering = ["name"]
        verbose_name = "Course"
        verbose_name_plural = "Courses"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Section(models.Model):
    """Academic section (e.g., Section A, Section B, STEM-11A)"""

    LEVEL_TYPE_CHOICES = [
        ("SHS", "Senior High School"),
        ("COL", "College"),
        ("BUN", "Bundled"),
        ("ALL", "All Levels"),
    ]

    name = models.CharField(max_length=100)
    level_type = models.CharField(
        max_length=3,
        choices=LEVEL_TYPE_CHOICES,
        default="SHS",
        help_text="Which level type this section belongs to",
    )
    grade_year = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Grade level or year (e.g., Grade 11, 1st Year)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sections"
        ordering = ["level_type", "grade_year", "name"]
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        unique_together = ["name", "level_type", "grade_year"]

    def __str__(self):
        grade = f" - {self.grade_year}" if self.grade_year else ""
        return f"{self.name}{grade} ({self.level_type})"
