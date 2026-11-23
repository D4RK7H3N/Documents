from rest_framework import serializers

from academics.models import Section, StudentProfile
from academics.serializers import create_student
from accounts.models import User
from audit.services import record_audit
from django.db import transaction

DEFAULT_SCHOOL_YEAR = "2026-2027"


class LearnerIngestSerializer(serializers.Serializer):
    lrn = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=100)
    middle_name = serializers.CharField(max_length=100, allow_blank=True, required=False, allow_null=True)
    last_name = serializers.CharField(max_length=100)
    section = serializers.CharField(max_length=50, allow_blank=True, required=False, allow_null=True)
    school_year = serializers.CharField(max_length=9, required=False, allow_blank=True, allow_null=True)
    grade_level = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)


class IngestSerializer(serializers.Serializer):
    students = LearnerIngestSerializer(many=True)


def _full_name(item):
    parts = [item.get("first_name", ""), item.get("middle_name") or "", item.get("last_name", "")]
    return " ".join(p.strip() for p in parts if p and p.strip())


def _normalize_grade_level(raw):
    value = (raw or "").strip().lower().replace(" ", "")
    if value in ("11", "g11", "grade11", "grade-11"):
        return "Grade 11"
    if value in ("12", "g12", "grade12", "grade-12"):
        return "Grade 12"
    return ""


def _section_for(item, school_year):
    from academics.models import Section

    section_name = (item.get("section") or "").strip()
    if not section_name:
        return None, None
    grade_level = _normalize_grade_level(item.get("grade_level")) or "Grade 12"
    section = Section.objects.filter(
        name__iexact=section_name, school_year=school_year, grade_level=grade_level
    ).first()
    if section is None:
        section = Section.objects.create(
            name=section_name, school_year=school_year, grade_level=grade_level
        )
    return section, grade_level


def ingest_students(items, source="school_pos"):
    created = []
    updated = []
    skipped = []
    with transaction.atomic():
        for item in items:
            lrn = (item.get("lrn") or "").strip()
            full_name = _full_name(item)
            school_year = (item.get("school_year") or "").strip() or DEFAULT_SCHOOL_YEAR
            raw_level = (item.get("grade_level") or "").strip()
            if raw_level and not _normalize_grade_level(raw_level):
                skipped.append({"lrn": lrn, "reason": f"Not an SHS learner ({raw_level})."})
                continue
            if not lrn.isdigit() or len(lrn) != 12:
                skipped.append({"lrn": lrn, "reason": "LRN must be exactly 12 digits."})
                continue
            if not full_name:
                skipped.append({"lrn": lrn, "reason": "Name is required."})
                continue
            profile = StudentProfile.objects.filter(lrn=lrn).select_related("user", "section").first()
            section, grade_level = _section_for(item, school_year)
            if profile is None:
                if section is None:
                    skipped.append({"lrn": lrn, "reason": "New learner has no section assigned yet."})
                    continue
                new_profile, _password = create_student(
                    lrn=lrn, full_name=full_name, section_id=section.id, created_by=None
                )
                created.append(
                    {"lrn": lrn, "full_name": full_name, "section": section.name, "grade_level": grade_level}
                )
                record_audit(
                    actor=None,
                    action="integration.student_created",
                    entity="student_profile",
                    entity_id=new_profile.id,
                    new_values={
                        "lrn": lrn,
                        "full_name": full_name,
                        "section": section.name,
                        "grade_level": grade_level,
                        "source": source,
                    },
                )
            else:
                old_name = profile.full_name
                old_section = profile.section.name if profile.section else None
                changes = {}
                if profile.full_name != full_name:
                    profile.full_name = full_name
                    changes["full_name"] = full_name
                if profile.section_id != section.id:
                    changes["section"] = section.name
                    profile.section = section
                if changes:
                    profile.save()
                    updated.append({"lrn": lrn, "changes": changes})
                    record_audit(
                        actor=None,
                        action="integration.student_updated",
                        entity="student_profile",
                        entity_id=profile.id,
                        old_values={"full_name": old_name, "section": old_section},
                        new_values={**changes, "source": source},
                    )
    return {"created": created, "updated": updated, "skipped": skipped}
