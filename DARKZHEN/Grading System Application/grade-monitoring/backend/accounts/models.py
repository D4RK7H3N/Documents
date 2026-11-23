import secrets
import string
import uuid
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

PASSWORD_ALPHABET = string.ascii_letters + string.digits


def generate_temporary_password(length=12):
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def avatar_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"avatars/{uuid.uuid4().hex}{extension}"


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=10, choices=Role.choices)
    must_change_password = models.BooleanField(default=True)
    phone = models.CharField(max_length=32, blank=True, default="")
    avatar = models.FileField(upload_to=avatar_upload_path, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["role"])]

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_locked_out(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    @property
    def display_name(self):
        if self.is_student:
            profile = getattr(self, "student_profile", None)
            return profile.full_name if profile else self.username
        if self.last_name or self.first_name:
            return f"{self.last_name}, {self.first_name}".strip(" ,")
        return self.username

    def register_failed_login(self, max_attempts=5, lockout_minutes=15):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timedelta(minutes=lockout_minutes)
            self.failed_login_attempts = 0
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def register_successful_login(self):
        if self.failed_login_attempts or self.locked_until:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save(update_fields=["failed_login_attempts", "locked_until"])

    def set_temporary_password(self):
        password = generate_temporary_password()
        self.set_password(password)
        self.must_change_password = True
        self.save(update_fields=["password", "must_change_password"])
        return password
