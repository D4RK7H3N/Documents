from rest_framework import serializers
from students.models import Student
from .models import Dropout


class DropoutSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    lrn = serializers.CharField(source='student.lrn', read_only=True)
    level_type = serializers.CharField(source='student.level_type', read_only=True)
    section = serializers.CharField(source='student.section', read_only=True)
    track_strand = serializers.CharField(source='student.track_strand', read_only=True)
    enrollment_status = serializers.CharField(source='student.enrollment_status', read_only=True)
    # Declared explicitly to drop the auto-generated UniqueValidator.
    # Dropout.student is a OneToOne and reinstatement keeps the row, so a
    # second dropout is a normal "reopen the record", not a duplicate. A
    # Meta.validators = [] is not enough: DRF attaches the unique check to the
    # field itself and rejects during is_valid(), before create() runs.
    student = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), validators=[]
    )

    def create(self, validated_data):
        """Reuse an existing record instead of failing on the unique student.

        Reinstatement flags the record as 'reinstated' rather than deleting it,
        so the history survives. But Dropout.student is a OneToOne, so a plain
        create() then raised "dropout with this student already exists" the
        next time the same student dropped out again - leaving their account
        stuck at 'Drop-out' with no way to record it. A repeat dropout reopens
        the existing record as confirmed.
        """
        from django.db import transaction

        student = validated_data.get("student")
        with transaction.atomic():
            existing = Dropout.objects.select_for_update().filter(student=student).first()
            if existing is None:
                return Dropout.objects.create(**validated_data)
            for field, value in validated_data.items():
                setattr(existing, field, value)
            existing.status = "confirmed"
            existing.reinstated_at = None
            existing.save()
            return existing

    class Meta:
        model = Dropout
        fields = [
            'id',
            'student',
            'student_name',
            'lrn',
            'level_type',
            'section',
            'track_strand',
            'enrollment_status',
            'dropout_date',
            'status',
            'reinstated_at',
            'last_grade_level',
            'last_section',
            'reason',
            'notes',
            'recorded_by',
            'created_at',
            'updated_at',
        ]
        # Dropout.student is a OneToOne, so DRF would attach a UniqueValidator
        # and reject a repeat dropout during is_valid() - before create() could
        # reopen the record. Reinstatement keeps the row for history, so this
        # is a normal situation rather than a genuine duplicate. create()
        # handles it instead.

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"