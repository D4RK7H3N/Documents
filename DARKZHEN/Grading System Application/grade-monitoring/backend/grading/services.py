from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from academics.models import ClassAssignment, StudentProfile
from audit.services import record_audit

from . import engine
from .models import (
    Assessment,
    GeneralAverage,
    GradeSubmission,
    GradingConfig,
    QuarterGrade,
    QuarterLock,
    Score,
    SemesterGrade,
)


def create_submission(*, class_assignment, quarter, submitted_by, to_teacher, note=""):
    if GradeSubmission.objects.filter(
        class_assignment=class_assignment, quarter=quarter, status=GradeSubmission.Status.PENDING
    ).exists():
        raise ValidationError({"detail": "A pending submission for this class and quarter already exists."})
    config = GradingConfig.get_active()
    students = list(StudentProfile.objects.filter(section=class_assignment.section).order_by("full_name"))
    quarter_grades = {
        g.student_id: g
        for g in QuarterGrade.objects.filter(
            student__in=students, subject=class_assignment.subject, quarter=quarter
        )
    }
    assessment_ids = list(class_assignment.assessments.filter(quarter=quarter).values_list("id", flat=True))
    filled = {}
    if assessment_ids:
        for student_id, raw in Score.objects.filter(
            student__in=students, assessment_id__in=assessment_ids
        ).values_list("student_id", "raw_score"):
            if raw is not None:
                filled[student_id] = filled.get(student_id, 0) + 1
    snapshot = []
    for student in students:
        g = quarter_grades.get(student.id)
        initial = g.initial_grade if g else None
        snapshot.append(
            {
                "lrn": student.lrn,
                "full_name": student.full_name,
                "grade": g.grade if g else None,
                "initial_grade": float(initial) if initial is not None else None,
                "blanks": (len(assessment_ids) - filled.get(student.id, 0)) if assessment_ids else 0,
            }
        )
    weights = class_assignment.subject.weights_override or config.weights_for(
        class_assignment.subject.subject_type
    )
    with transaction.atomic():
        submission = GradeSubmission.objects.create(
            class_assignment=class_assignment,
            quarter=quarter,
            submitted_by=submitted_by,
            submitted_to=to_teacher,
            note=note,
            snapshot=snapshot,
        )
        record_audit(
            actor=submitted_by,
            action="submission.create",
            entity="grade_submission",
            entity_id=submission.id,
            new_values={
                "class_assignment": class_assignment.id,
                "quarter": quarter,
                "to": to_teacher.display_name,
                "learners": len(snapshot),
                "weights": weights,
            },
        )
    return submission


def decide_submission(*, submission, decided_by, approve, decision_note=""):
    if submission.submitted_to_id != decided_by.id and not decided_by.is_admin:
        raise PermissionDenied("Only the receiving teacher can decide this submission.")
    if submission.status != GradeSubmission.Status.PENDING:
        raise ValidationError({"detail": f"This submission was already {submission.status}."})
    from django.utils import timezone

    submission.status = (
        GradeSubmission.Status.APPROVED if approve else GradeSubmission.Status.RETURNED
    )
    submission.decision_note = decision_note
    submission.decided_by = decided_by
    submission.decided_at = timezone.now()
    submission.save(update_fields=["status", "decision_note", "decided_by", "decided_at"])
    record_audit(
        actor=decided_by,
        action="submission.approve" if approve else "submission.return",
        entity="grade_submission",
        entity_id=submission.id,
        old_values={"status": GradeSubmission.Status.PENDING},
        new_values={"status": submission.status, "decision_note": decision_note},
    )
    return submission


def semester_for_quarter(quarter):
    return 1 if quarter in (1, 2) else 2


def quarter_is_locked(class_assignment, quarter):
    return QuarterLock.objects.filter(class_assignment=class_assignment, quarter=quarter).exists()


def component_sums_for(student, class_assignment, quarter):
    rows = Score.objects.filter(
        student=student,
        assessment__class_assignment=class_assignment,
        assessment__quarter=quarter,
    ).values_list("assessment__component", "raw_score", "assessment__highest_possible_score")
    return engine.component_sums_from_scores(rows)


def recompute_quarter(student, class_assignment, quarter):
    config = GradingConfig.get_active()
    subject = class_assignment.subject
    sums = component_sums_for(student, class_assignment, quarter)
    weights = subject.weights_override or config.weights_for(subject.subject_type)
    has_any = engine.has_scores(sums)
    initial = engine.initial_grade(sums, weights) if has_any else None
    grade = engine.transmute(initial, config.transmutation_table) if has_any else None
    QuarterGrade.objects.update_or_create(
        student=student,
        subject=subject,
        quarter=quarter,
        defaults={"grade": grade, "initial_grade": initial},
    )
    recompute_semester(student, subject, semester_for_quarter(quarter))


def recompute_semester(student, subject, semester):
    quarters = (semester * 2 - 1, semester * 2)
    grades = list(
        QuarterGrade.objects.filter(student=student, subject=subject, quarter__in=quarters)
        .values_list("quarter", "grade")
    )
    by_quarter = dict(grades)
    ordered = [by_quarter.get(q) for q in quarters]
    if not grades:
        final = None
    else:
        final = engine.semester_final(ordered)
    SemesterGrade.objects.update_or_create(
        student=student, subject=subject, semester=semester, defaults={"final": final}
    )
    recompute_general_average(student, semester)


def recompute_general_average(student, semester):
    subject_ids = list(
        ClassAssignment.objects.filter(section=student.section).values_list("subject_id", flat=True)
    )
    final_map = dict(
        SemesterGrade.objects.filter(
            student=student, semester=semester, subject_id__in=subject_ids
        ).values_list("subject_id", "final")
    )
    finals = [final_map.get(subject_id) for subject_id in subject_ids]
    GeneralAverage.objects.update_or_create(
        student=student,
        semester=semester,
        defaults={"average": engine.general_average(finals) if subject_ids else None},
    )


def recompute_students(students, class_assignment, quarter):
    for student in students:
        recompute_quarter(student, class_assignment, quarter)


def recompute_all():
    for assignment in ClassAssignment.objects.select_related("subject", "section"):
        students = StudentProfile.objects.filter(section=assignment.section)
        for quarter in (1, 2, 3, 4):
            recompute_students(students, assignment, quarter)


def save_scores(assessment, entries, actor):
    hps = assessment.highest_possible_score
    student_ids = [entry["student_id"] for entry in entries]
    students = {
        s.id: s
        for s in StudentProfile.objects.filter(id__in=student_ids, section=assessment.class_assignment.section)
    }
    invalid_ids = [sid for sid in student_ids if sid not in students]
    if invalid_ids:
        raise ValidationError({"scores": [f"Students {invalid_ids} are not enrolled in this class."]})
    for entry in entries:
        raw = entry.get("raw", None)
        if raw is not None and raw < 0:
            raise ValidationError({"scores": ["Scores cannot be negative."]})
        if raw is not None and raw > hps:
            raise ValidationError(
                {"scores": [f"Score {raw} exceeds the highest possible score {hps}."]}
            )
    old_values = {}
    new_values = {}
    changed_students = []
    with transaction.atomic():
        existing = {
            score.student_id: score
            for score in Score.objects.filter(assessment=assessment, student_id__in=student_ids)
        }
        for entry in entries:
            raw = entry.get("raw", None)
            student = students[entry["student_id"]]
            score = existing.get(student.id)
            old = score.raw_score if score else None
            if score is None:
                Score.objects.create(assessment=assessment, student=student, raw_score=raw)
            else:
                score.raw_score = raw
                score.save(update_fields=["raw_score", "updated_at"])
            if old != raw:
                old_values[str(student.id)] = str(old) if old is not None else None
                new_values[str(student.id)] = str(raw) if raw is not None else None
                changed_students.append(student)
        if changed_students:
            record_audit(
                actor=actor,
                action="score.save",
                entity="assessment",
                entity_id=assessment.id,
                old_values=old_values,
                new_values=new_values,
            )
            recompute_students(changed_students, assessment.class_assignment, assessment.quarter)
    return len(entries), len(changed_students)


def create_assessment(*, class_assignment, component, quarter, title, highest_possible_score, actor):
    with transaction.atomic():
        assessment = Assessment.objects.create(
            class_assignment=class_assignment,
            component=component,
            quarter=quarter,
            title=title,
            highest_possible_score=highest_possible_score,
        )
        record_audit(
            actor=actor,
            action="assessment.create",
            entity="assessment",
            entity_id=assessment.id,
            new_values={
                "class_assignment": class_assignment.id,
                "component": component,
                "quarter": quarter,
                "title": title,
                "highest_possible_score": str(highest_possible_score),
            },
        )
    return assessment


def update_assessment(assessment, data, actor):
    old = {
        "component": assessment.component,
        "quarter": assessment.quarter,
        "title": assessment.title,
        "highest_possible_score": str(assessment.highest_possible_score),
    }
    hps_changed = False
    with transaction.atomic():
        for field, value in data.items():
            setattr(assessment, field, value)
            if field == "highest_possible_score":
                hps_changed = True
        assessment.save()
        record_audit(
            actor=actor,
            action="assessment.update",
            entity="assessment",
            entity_id=assessment.id,
            old_values=old,
            new_values={
                "component": assessment.component,
                "quarter": assessment.quarter,
                "title": assessment.title,
                "highest_possible_score": str(assessment.highest_possible_score),
            },
        )
        if hps_changed or "quarter" in data or "component" in data:
            students = StudentProfile.objects.filter(section=assessment.class_assignment.section)
            recompute_students(students, assessment.class_assignment, assessment.quarter)
            if "quarter" in data and old["quarter"] != assessment.quarter:
                recompute_students(students, assessment.class_assignment, old["quarter"])
    return assessment


def delete_assessment(assessment, actor):
    with transaction.atomic():
        affected_ids = list(assessment.scores.values_list("student_id", flat=True))
        snapshot = {
            "component": assessment.component,
            "quarter": assessment.quarter,
            "title": assessment.title,
            "highest_possible_score": str(assessment.highest_possible_score),
        }
        assessment.delete()
        record_audit(
            actor=actor,
            action="assessment.delete",
            entity="assessment",
            entity_id=snapshot["title"],
            old_values=snapshot,
        )
        students = StudentProfile.objects.filter(id__in=affected_ids)
        recompute_students(students, assessment.class_assignment, snapshot["quarter"])


def set_quarter_lock(class_assignment, quarter, actor, locked=True):
    with transaction.atomic():
        if locked:
            _, created = QuarterLock.objects.get_or_create(
                class_assignment=class_assignment, quarter=quarter, defaults={"locked_by": actor}
            )
            if not created:
                raise ValidationError({"detail": "Quarter is already locked."})
        else:
            deleted, _ = QuarterLock.objects.filter(
                class_assignment=class_assignment, quarter=quarter
            ).delete()
            if not deleted:
                raise ValidationError({"detail": "Quarter is not locked."})
        record_audit(
            actor=actor,
            action="quarter.lock" if locked else "quarter.unlock",
            entity="class_assignment",
            entity_id=class_assignment.id,
            new_values={"quarter": quarter},
        )


def update_grading_config(config, data, actor):
    with transaction.atomic():
        old = {"weights": config.weights, "transmutation_table": config.transmutation_table}
        for field, value in data.items():
            setattr(config, field, value)
        config.updated_by = actor
        config.save()
        record_audit(
            actor=actor,
            action="grading_config.update",
            entity="grading_config",
            entity_id=config.id,
            old_values=old,
            new_values={"weights": config.weights, "transmutation_table": config.transmutation_table},
        )
        recompute_all()
    return config
