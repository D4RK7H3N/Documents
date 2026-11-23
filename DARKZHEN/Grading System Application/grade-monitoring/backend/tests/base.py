from django.core.cache import cache

from accounts.models import User
from academics.models import ClassAssignment, Section, StudentProfile, Subject
from academics.serializers import create_student


def make_user(username, password, role, must_change=False):
    user = User.objects.create_user(username=username, password=password, role=role)
    user.must_change_password = must_change
    user.save()
    return user


def make_section(name="Lovelace", school_year="2026-2027"):
    return Section.objects.create(name=name, school_year=school_year)


def make_subject(name="General Physics 1", subject_type="core"):
    return Subject.objects.create(name=name, subject_type=subject_type)


def make_assignment(subject, section, teacher, school_year="2026-2027"):
    return ClassAssignment.objects.create(
        subject=subject, section=section, teacher=teacher, school_year=school_year
    )


def make_student(lrn, full_name, section, created_by, force_ready=True):
    profile, password = create_student(lrn=lrn, full_name=full_name, section_id=section.id, created_by=created_by)
    if force_ready:
        profile.user.must_change_password = False
        profile.user.save()
    return profile, password


def login(client, username, password):
    cache.clear()
    return client.post("/api/v1/auth/login/", {"username": username, "password": password}, format="json")


def auth(client, token):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
