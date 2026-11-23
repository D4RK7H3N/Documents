import csv
import io

from django.db import transaction
from rest_framework import serializers

from accounts.models import User
from audit.services import record_audit

from .models import ClassAssignment, Section, StudentProfile, Subject


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["id", "name", "school_year", "grade_level"]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "subject_type", "weights_override"]

    def validate_weights_override(self, value):
        if value in (None, ""):
            return None
        if not isinstance(value, dict):
            raise serializers.ValidationError("Weights must be an object with WW, PT and QA keys.")
        required = ("WW", "PT", "QA")
        for key in required:
            if key not in value:
                raise serializers.ValidationError(f"Missing weight for {key}.")
        try:
            total = sum(float(value[key]) for key in required)
        except (TypeError, ValueError):
            raise serializers.ValidationError("Weights must be numbers.")
        if any(float(value[key]) < 0 for key in required):
            raise serializers.ValidationError("Weights cannot be negative.")
        if abs(total - 100) > 0.01:
            raise serializers.ValidationError("Weights must total exactly 100%.")
        return {key: str(value[key]) for key in required}


class ClassAssignmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.username", read_only=True)
    locked_quarters = serializers.SerializerMethodField()

    class Meta:
        model = ClassAssignment
        fields = [
            "id",
            "subject",
            "subject_name",
            "section",
            "section_name",
            "teacher",
            "teacher_name",
            "school_year",
            "locked_quarters",
        ]

    def get_locked_quarters(self, obj):
        return list(obj.quarter_locks.values_list("quarter", flat=True))


class StudentProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    grade_level = serializers.CharField(source="section.grade_level", read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "user",
            "lrn",
            "full_name",
            "section",
            "section_name",
            "grade_level",
            "username",
            "is_active",
        ]


class StudentCreateSerializer(serializers.Serializer):
    lrn = serializers.CharField(max_length=12)
    full_name = serializers.CharField(max_length=150)
    section = serializers.IntegerField()
    grade_level = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_lrn(self, value):
        if not value.isdigit() or len(value) != 12:
            raise serializers.ValidationError("LRN must be exactly 12 digits.")
        if StudentProfile.objects.filter(lrn=value).exists():
            raise serializers.ValidationError("A student with this LRN already exists.")
        return value

    def validate_section(self, value):
        if not Section.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Section not found.")
        return value


class StudentUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, required=False)
    section = serializers.IntegerField(required=False)

    def validate_section(self, value):
        if not Section.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Section not found.")
        return value

    def save(self, *, profile, actor):
        from audit.services import record_audit

        old = {"full_name": profile.full_name, "section": profile.section.name}
        changes = {}
        if "full_name" in self.validated_data and self.validated_data["full_name"] != profile.full_name:
            profile.full_name = self.validated_data["full_name"]
            changes["full_name"] = profile.full_name
        if "section" in self.validated_data and profile.section_id != self.validated_data["section"]:
            profile.section_id = self.validated_data["section"]
            changes["section"] = profile.section.name
        if changes:
            profile.save()
            record_audit(
                actor=actor,
                action="student.update",
                entity="student_profile",
                entity_id=profile.id,
                old_values=old,
                new_values=changes,
            )
        return profile, changes


def create_staff_account(*, username, role):
    from accounts.models import User

    if User.objects.filter(username__iexact=username).exists():
        return None, None, "Username already exists."
    user = User.objects.create_user(username=username, role=role)
    password = user.set_temporary_password()
    return user, password, None


def create_student(*, lrn, full_name, section_id, created_by):
    section = Section.objects.get(pk=section_id)
    with transaction.atomic():
        user = User.objects.create_user(username=lrn, password=None, role=User.Role.STUDENT)
        password = user.set_temporary_password()
        profile = StudentProfile.objects.create(user=user, lrn=lrn, full_name=full_name, section=section)
        record_audit(
            actor=created_by,
            action="student.create",
            entity="student_profile",
            entity_id=profile.id,
            new_values={"lrn": lrn, "full_name": full_name, "section": section.name},
        )
    return profile, password


def import_students_csv(*, file, created_by):
    results = []
    errors = []
    decoded = file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames or "lrn" not in reader.fieldnames:
        return None, ["CSV must have a header row with at least an 'lrn' column."]
    for row_num, row in enumerate(reader, start=2):
        lrn = (row.get("lrn") or "").strip()
        full_name = (row.get("name") or row.get("full_name") or "").strip()
        section_name = (row.get("section") or "").strip()
        if not lrn or not full_name or not section_name:
            errors.append({"row": row_num, "error": "lrn, name and section are required."})
            continue
        if len(lrn) != 12 or not lrn.isdigit():
            errors.append({"row": row_num, "error": f"Invalid LRN '{lrn}'."})
            continue
        section = Section.objects.filter(name__iexact=section_name).first()
        if not section:
            errors.append({"row": row_num, "error": f"Section '{section_name}' not found."})
            continue
        if StudentProfile.objects.filter(lrn=lrn).exists():
            errors.append({"row": row_num, "error": f"LRN {lrn} already exists."})
            continue
        profile, password = create_student(lrn=lrn, full_name=full_name, section_id=section.id, created_by=created_by)
        results.append({"lrn": lrn, "full_name": full_name, "temporary_password": password})
    record_audit(
        actor=created_by,
        action="student.import",
        entity="student_profile",
        new_values={"imported": len(results), "failed": len(errors)},
    )
    return results, errors
