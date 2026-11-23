from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from academics.models import ClassAssignment, StudentProfile
from accounts.models import User
from common.permissions import IsAdmin, IsStudent, IsTeacherOrAdmin

from .models import Assessment, GeneralAverage, GradeSubmission, GradingConfig, QuarterGrade, Score, SemesterGrade
from .serializers import AssessmentSerializer, BulkScoresSerializer, GradingConfigSerializer
from . import services


def get_class(user, class_id):
    class_assignment = get_object_or_404(
        ClassAssignment.objects.select_related("subject", "section", "teacher"), pk=class_id
    )
    ensure_can_manage_class(user, class_assignment)
    return class_assignment


def ensure_can_manage_class(user, class_assignment):
    if user.is_admin:
        return
    if user.role == "teacher" and class_assignment.teacher_id == user.id:
        return
    raise PermissionDenied("You are not assigned to this class.")


class ClassAssessmentsView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, class_id):
        class_assignment = get_class(request.user, class_id)
        qs = class_assignment.assessments.all()
        quarter = request.query_params.get("quarter")
        if quarter:
            qs = qs.filter(quarter=quarter)
        return Response(AssessmentSerializer(qs, many=True).data)

    def post(self, request, class_id):
        class_assignment = get_class(request.user, class_id)
        serializer = AssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if request.user.role == "teacher" and services.quarter_is_locked(class_assignment, data["quarter"]):
            return Response(
                {"error": {"code": "conflict", "message": "This quarter is locked. Ask an administrator to unlock it."}},
                status=status.HTTP_409_CONFLICT,
            )
        assessment = services.create_assessment(
            class_assignment=class_assignment,
            component=data["component"],
            quarter=data["quarter"],
            title=data["title"],
            highest_possible_score=data["highest_possible_score"],
            actor=request.user,
        )
        return Response(AssessmentSerializer(assessment).data, status=status.HTTP_201_CREATED)


class AssessmentDetailView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def patch(self, request, assessment_id):
        assessment = get_object_or_404(Assessment.objects.select_related("class_assignment"), pk=assessment_id)
        get_class(request.user, assessment.class_assignment_id)
        serializer = AssessmentSerializer(assessment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data.pop("class_assignment", None)
        if request.user.role == "teacher":
            affected_quarters = {assessment.quarter}
            if "quarter" in data:
                affected_quarters.add(data["quarter"])
            if any(services.quarter_is_locked(assessment.class_assignment, q) for q in affected_quarters):
                return Response(
                    {"error": {"code": "conflict", "message": "This quarter is locked."}},
                    status=status.HTTP_409_CONFLICT,
                )
        services.update_assessment(assessment, data, request.user)
        return Response(AssessmentSerializer(assessment).data)

    def delete(self, request, assessment_id):
        assessment = get_object_or_404(Assessment.objects.select_related("class_assignment"), pk=assessment_id)
        get_class(request.user, assessment.class_assignment_id)
        if request.user.role == "teacher" and services.quarter_is_locked(
            assessment.class_assignment, assessment.quarter
        ):
            return Response(
                {"error": {"code": "conflict", "message": "This quarter is locked."}},
                status=status.HTTP_409_CONFLICT,
            )
        services.delete_assessment(assessment, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssessmentScoresView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, assessment_id):
        assessment = get_object_or_404(Assessment.objects.select_related("class_assignment"), pk=assessment_id)
        get_class(request.user, assessment.class_assignment_id)
        scores = {s.student_id: s.raw_score for s in assessment.scores.all()}
        students = StudentProfile.objects.filter(section=assessment.class_assignment.section).order_by("full_name")
        rows = [
            {
                "student_id": student.id,
                "lrn": student.lrn,
                "full_name": student.full_name,
                "raw": scores.get(student.id),
            }
            for student in students
        ]
        return Response({"assessment": AssessmentSerializer(assessment).data, "students": rows})

    def put(self, request, assessment_id):
        assessment = get_object_or_404(Assessment.objects.select_related("class_assignment"), pk=assessment_id)
        get_class(request.user, assessment.class_assignment_id)
        if request.user.role == "teacher" and services.quarter_is_locked(
            assessment.class_assignment, assessment.quarter
        ):
            return Response(
                {"error": {"code": "conflict", "message": "This quarter is locked. Ask an administrator to unlock it."}},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = BulkScoresSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        received, changed = services.save_scores(assessment, serializer.validated_data["scores"], request.user)
        return Response({"received": received, "changed": changed})


class ClassGradesView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, class_id):
        class_assignment = get_class(request.user, class_id)
        quarter = request.query_params.get("quarter", "1")
        if quarter not in ("1", "2", "3", "4"):
            raise ValidationError({"quarter": "Quarter must be 1, 2, 3 or 4."})
        quarter = int(quarter)
        students = list(
            StudentProfile.objects.filter(section=class_assignment.section).order_by("full_name")
        )
        assessment_ids = set(
            class_assignment.assessments.filter(quarter=quarter).values_list("id", flat=True)
        )
        grades = {
            g.student_id: g
            for g in QuarterGrade.objects.filter(
                student__in=students, subject=class_assignment.subject, quarter=quarter
            )
        }
        filled = {}
        for student_id, raw in Score.objects.filter(
            student__in=students, assessment_id__in=assessment_ids
        ).values_list("student_id", "raw_score"):
            if raw is not None:
                filled[student_id] = filled.get(student_id, 0) + 1
        rows = []
        for student in students:
            grade = grades.get(student.id)
            blanks = (len(assessment_ids) - filled.get(student.id, 0)) if assessment_ids else 0
            rows.append(
                {
                    "student_id": student.id,
                    "lrn": student.lrn,
                    "full_name": student.full_name,
                    "grade": grade.grade if grade else None,
                    "initial_grade": grade.initial_grade if grade else None,
                    "blanks": blanks,
                }
            )
        return Response(
            {
                "class": {
                    "id": class_assignment.id,
                    "subject": class_assignment.subject.name,
                    "section": class_assignment.section.name,
                },
                "locked_quarters": list(
                    class_assignment.quarter_locks.values_list("quarter", flat=True)
                ),
                "quarter": quarter,
                "students": rows,
            }
        )


class MyGradesView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        student = request.user.student_profile
        semester = request.query_params.get("semester", "1")
        if semester not in ("1", "2"):
            raise ValidationError({"semester": "Semester must be 1 or 2."})
        semester = int(semester)
        quarters = (semester * 2 - 1, semester * 2)
        assignments = ClassAssignment.objects.filter(section=student.section).select_related("subject")
        quarter_grades = {
            (g.subject_id, g.quarter): g
            for g in QuarterGrade.objects.filter(student=student, quarter__in=quarters)
        }
        semester_grades = {
            g.subject_id: g.final
            for g in SemesterGrade.objects.filter(student=student, semester=semester)
        }
        subjects = []
        for assignment in assignments:
            q1 = quarter_grades.get((assignment.subject_id, quarters[0]))
            q2 = quarter_grades.get((assignment.subject_id, quarters[1]))
            subjects.append(
                {
                    "subject": assignment.subject.name,
                    "q1": q1.grade if q1 else None,
                    "q2": q2.grade if q2 else None,
                    "final": semester_grades.get(assignment.subject_id),
                }
            )
        average = GeneralAverage.objects.filter(student=student, semester=semester).first()
        latest = QuarterGrade.objects.filter(student=student).order_by("-computed_at").first()
        return Response(
            {
                "student": {
                    "lrn": student.lrn,
                    "name": student.full_name,
                    "section": student.section.name,
                },
                "semester": semester,
                "subjects": subjects,
                "general_average": average.average if average else None,
                "last_updated": latest.computed_at if latest else None,
            }
        )


def _submission_payload(submission):
    return {
        "id": submission.id,
        "class": {
            "id": submission.class_assignment_id,
            "subject": submission.class_assignment.subject.name,
            "section": submission.class_assignment.section.name,
        },
        "quarter": submission.quarter,
        "submitted_by": submission.submitted_by.display_name,
        "submitted_to": submission.submitted_to.display_name,
        "status": submission.status,
        "note": submission.note,
        "decision_note": submission.decision_note,
        "created_at": submission.created_at,
        "decided_at": submission.decided_at,
        "snapshot": submission.snapshot,
    }


class SubmissionView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        box = request.query_params.get("box", "received")
        qs = GradeSubmission.objects.select_related(
            "class_assignment__subject", "class_assignment__section", "submitted_by", "submitted_to"
        ).all()
        if box == "sent":
            qs = qs.filter(submitted_by=request.user)
        else:
            qs = qs.filter(submitted_to=request.user)
        return Response([_submission_payload(s) for s in qs[:100]])


class SubmissionCreateView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, class_id):
        class_assignment = get_object_or_404(
            ClassAssignment.objects.select_related("subject", "section"), pk=class_id
        )
        ensure_can_manage_class(request.user, class_assignment)
        quarter = request.data.get("quarter")
        if quarter not in (1, 2, 3, 4):
            raise ValidationError({"quarter": "Quarter must be 1, 2, 3 or 4."})
        to_teacher = get_object_or_404(User, pk=request.data.get("to_teacher_id"), role="teacher", is_active=True)
        if to_teacher.id == request.user.id:
            raise ValidationError({"to_teacher_id": "Choose a different teacher."})
        submission = services.create_submission(
            class_assignment=class_assignment,
            quarter=quarter,
            submitted_by=request.user,
            to_teacher=to_teacher,
            note=(request.data.get("note") or "").strip(),
        )
        return Response(_submission_payload(submission), status=status.HTTP_201_CREATED)


class SubmissionDecisionView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, submission_id, decision):
        submission = get_object_or_404(GradeSubmission, pk=submission_id)
        if decision not in ("approve", "return"):
            raise ValidationError({"detail": "Unknown decision."})
        submission = services.decide_submission(
            submission=submission,
            decided_by=request.user,
            approve=(decision == "approve"),
            decision_note=(request.data.get("decision_note") or "").strip(),
        )
        return Response(_submission_payload(submission))


class StudentRecordView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, student_id):
        student = get_object_or_404(
            StudentProfile.objects.select_related("user", "section"), pk=student_id
        )
        if request.user.role == "teacher":
            assigned_sections = ClassAssignment.objects.filter(
                teacher=request.user
            ).values_list("section_id", flat=True)
            if student.section_id not in assigned_sections:
                raise PermissionDenied("You can only view records of learners in your assigned classes.")
        assignments = ClassAssignment.objects.filter(section=student.section).select_related("subject")
        quarter_grades = {
            (g.subject_id, g.quarter): g.grade
            for g in QuarterGrade.objects.filter(student=student)
        }
        semester_grades = {
            (g.subject_id, g.semester): g.final
            for g in SemesterGrade.objects.filter(student=student)
        }
        averages = {g.semester: g.average for g in GeneralAverage.objects.filter(student=student)}
        subjects = []
        for assignment in assignments:
            s = assignment.subject
            subjects.append(
                {
                    "subject": s.name,
                    "subject_type": s.subject_type,
                    "q1": quarter_grades.get((s.id, 1)),
                    "q2": quarter_grades.get((s.id, 2)),
                    "q3": quarter_grades.get((s.id, 3)),
                    "q4": quarter_grades.get((s.id, 4)),
                    "s1": semester_grades.get((s.id, 1)),
                    "s2": semester_grades.get((s.id, 2)),
                }
            )
        latest = QuarterGrade.objects.filter(student=student).order_by("-computed_at").first()
        return Response(
            {
                "student": {
                    "lrn": student.lrn,
                    "name": student.full_name,
                    "section": student.section.name,
                    "grade_level": student.section.grade_level,
                    "school_year": student.section.school_year,
                },
                "subjects": subjects,
                "general_averages": {"s1": averages.get(1), "s2": averages.get(2)},
                "last_updated": latest.computed_at if latest else None,
            }
        )


class SectionReportView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, section_id):
        from academics.models import Section

        section = get_object_or_404(Section.objects.select_related(), pk=section_id)
        if request.user.role == "teacher":
            teaches_section = ClassAssignment.objects.filter(
                teacher=request.user, section=section
            ).exists()
            if not teaches_section:
                raise PermissionDenied("You can only view reports of sections you teach in.")

        semester = request.query_params.get("semester", "1")
        if semester not in ("1", "2"):
            raise ValidationError({"semester": "Semester must be 1 or 2."})
        semester = int(semester)

        assignments = list(
            ClassAssignment.objects.filter(section=section).select_related("subject").order_by("subject__name")
        )
        students = list(
            StudentProfile.objects.filter(section=section).order_by("full_name")
        )
        finals = {
            (g.student_id, g.subject_id): g.final
            for g in SemesterGrade.objects.filter(
                student__in=students, semester=semester, subject__in=[a.subject for a in assignments]
            )
        }
        averages = {g.student_id: g.average for g in GeneralAverage.objects.filter(student__in=students, semester=semester)}

        rows = []
        for student in students:
            subject_finals = [finals.get((student.id, a.subject_id)) for a in assignments]
            rows.append(
                {
                    "student_id": student.id,
                    "lrn": student.lrn,
                    "full_name": student.full_name,
                    "finals": subject_finals,
                    "general_average": averages.get(student.id),
                }
            )
        return Response(
            {
                "section": {"id": section.id, "name": section.name, "grade_level": section.grade_level},
                "semester": semester,
                "subjects": [{"id": a.subject_id, "name": a.subject.name, "type": a.subject.subject_type} for a in assignments],
                "students": rows,
            }
        )


class ClassSemesterReportView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, class_id):
        class_assignment = get_class(request.user, class_id)
        semester = request.query_params.get("semester", "1")
        if semester not in ("1", "2"):
            raise ValidationError({"semester": "Semester must be 1 or 2."})
        semester = int(semester)
        quarters = (semester * 2 - 1, semester * 2)
        students = list(
            StudentProfile.objects.filter(section=class_assignment.section).order_by("full_name")
        )
        quarter_grades = {
            (g.student_id, g.quarter): g
            for g in QuarterGrade.objects.filter(
                student__in=students, subject=class_assignment.subject, quarter__in=quarters
            )
        }
        semester_grades = {
            g.student_id: g.final
            for g in SemesterGrade.objects.filter(
                student__in=students, subject=class_assignment.subject, semester=semester
            )
        }
        assessment_ids_by_quarter = {
            q: set(class_assignment.assessments.filter(quarter=q).values_list("id", flat=True))
            for q in quarters
        }
        filled_by_quarter = {q: {} for q in quarters}
        for q in quarters:
            if assessment_ids_by_quarter[q]:
                for student_id, raw in Score.objects.filter(
                    student__in=students, assessment_id__in=assessment_ids_by_quarter[q]
                ).values_list("student_id", "raw_score"):
                    if raw is not None:
                        filled_by_quarter[q][student_id] = filled_by_quarter[q].get(student_id, 0) + 1
        rows = []
        for student in students:
            q1 = quarter_grades.get((student.id, quarters[0]))
            q2 = quarter_grades.get((student.id, quarters[1]))
            blanks = {}
            for q in quarters:
                total = len(assessment_ids_by_quarter[q])
                filled = filled_by_quarter[q].get(student.id, 0)
                blanks[q] = (total - filled) if total else 0
            rows.append(
                {
                    "student_id": student.id,
                    "lrn": student.lrn,
                    "full_name": student.full_name,
                    f"q{quarters[0]}": q1.grade if q1 else None,
                    f"q{quarters[1]}": q2.grade if q2 else None,
                    "final": semester_grades.get(student.id),
                    f"blanks_q{quarters[0]}": blanks[quarters[0]],
                    f"blanks_q{quarters[1]}": blanks[quarters[1]],
                }
            )
        finals = [r["final"] for r in rows if r["final"] is not None]
        class_final = (
            round(sum(finals) / len(finals)) if len(finals) == len(rows) and rows else None
        )
        return Response(
            {
                "class": {
                    "id": class_assignment.id,
                    "subject": class_assignment.subject.name,
                    "section": class_assignment.section.name,
                },
                "semester": semester,
                "students": rows,
                "class_final": class_final,
                "complete": bool(rows) and all(r["final"] is not None for r in rows),
            }
        )


class GradingConfigView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(GradingConfigSerializer(GradingConfig.get_active()).data)

    def put(self, request):
        config = GradingConfig.get_active()
        serializer = GradingConfigSerializer(config, data=request.data)
        serializer.is_valid(raise_exception=True)
        services.update_grading_config(config, serializer.validated_data, request.user)
        return Response(GradingConfigSerializer(config).data)


class QuarterLockView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, class_id, quarter):
        if quarter not in (1, 2, 3, 4):
            raise ValidationError({"quarter": "Quarter must be 1, 2, 3 or 4."})
        class_assignment = get_class(request.user, class_id)
        services.set_quarter_lock(class_assignment, quarter, request.user, locked=True)
        return Response({"class_id": class_assignment.id, "quarter": quarter, "locked": True})

    def delete(self, request, class_id, quarter):
        if quarter not in (1, 2, 3, 4):
            raise ValidationError({"quarter": "Quarter must be 1, 2, 3 or 4."})
        class_assignment = get_class(request.user, class_id)
        services.set_quarter_lock(class_assignment, quarter, request.user, locked=False)
        return Response({"class_id": class_assignment.id, "quarter": quarter, "locked": False})
