from rest_framework import serializers
from .models import Track, Strand, Course, Section


class StrandSerializer(serializers.ModelSerializer):
    """Serializer for strands"""

    track_name = serializers.CharField(source="track.name", read_only=True)
    track_code = serializers.CharField(source="track.code", read_only=True)
    # The track's audience (SHS/COL/BUN/ALL) so section forms can filter
    # strand options by the selected grade level.
    track_level_type = serializers.CharField(source="track.level_type", read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Strand
        fields = [
            "id",
            "track",
            "track_name",
            "track_code",
            "track_level_type",
            "name",
            "code",
            "description",
            "full_name",
            "is_active",
            "created_at",
            "updated_at",
        ]


class TrackSerializer(serializers.ModelSerializer):
    """Serializer for tracks"""

    strands = StrandSerializer(many=True, read_only=True)
    strand_count = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = [
            "id",
            "name",
            "code",
            "description",
            "level_type",
            "is_active",
            "strands",
            "strand_count",
            "student_count",
            "created_at",
            "updated_at",
        ]

    def get_strand_count(self, obj):
        return obj.strands.filter(is_active=True).count()

    def get_student_count(self, obj):
        from students.models import Student
        return Student.objects.filter(strand__track=obj).count()


class TrackListSerializer(serializers.ModelSerializer):
    """Simplified serializer for track lists/dropdowns"""

    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = ["id", "name", "code", "level_type", "is_active", "student_count"]

    def get_student_count(self, obj):
        from students.models import Student
        return Student.objects.filter(strand__track=obj).count()


class StrandListSerializer(serializers.ModelSerializer):
    """Simplified serializer for strand lists/dropdowns"""

    track_name = serializers.CharField(source="track.name", read_only=True)
    track_code = serializers.CharField(source="track.code", read_only=True)
    track_level_type = serializers.CharField(source="track.level_type", read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Strand
        fields = [
            "id",
            "name",
            "code",
            "track",
            "track_name",
            "track_code",
            "track_level_type",
            "display_name",
            "is_active",
        ]

    def get_display_name(self, obj):
        return f"{obj.name} ({obj.code})"


class StrandCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating strands with auto-create track"""

    track_name = serializers.CharField(required=False, allow_blank=True)
    track_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Strand
        fields = [
            "id",
            "track",
            "track_name",
            "track_code",
            "name",
            "code",
            "description",
            "is_active",
        ]
        extra_kwargs = {"track": {"required": False}}

    def create(self, validated_data):
        track_name = validated_data.pop("track_name", None)
        track_code = validated_data.pop("track_code", None)
        track = validated_data.get("track")

        # If no track provided, try to get or create from name/code
        if not track and (track_name or track_code):
            if track_code:
                track, _ = Track.objects.get_or_create(
                    code=track_code.upper(),
                    defaults={"name": track_name or track_code, "level_type": "SHS"},
                )
            elif track_name:
                # Generate code from name
                code = "".join(word[0] for word in track_name.split()[:4]).upper()
                track, _ = Track.objects.get_or_create(
                    code=code, defaults={"name": track_name, "level_type": "SHS"}
                )
            validated_data["track"] = track

        return super().create(validated_data)


class TrackStrandAutoCreateSerializer(serializers.Serializer):
    """
    Serializer for auto-creating track/strand from a single string input.
    Supports formats like:
    - "STEM" - Creates strand with auto-generated track
    - "Academic - STEM" - Creates track "Academic" and strand "STEM"
    - Just typing a name will auto-create both track and strand
    """

    name = serializers.CharField(max_length=200)
    level_type = serializers.ChoiceField(
        choices=[("SHS", "SHS"), ("COL", "COL"), ("BUN", "BUN"), ("ALL", "ALL")],
        default="SHS",
    )

    def create(self, validated_data):
        name = validated_data["name"].strip()
        level_type = validated_data.get("level_type", "SHS")

        # Check if it contains a separator (Track - Strand format)
        if " - " in name:
            track_name, strand_name = name.split(" - ", 1)
            track_name = track_name.strip()
            strand_name = strand_name.strip()
        else:
            # Single name - use as strand name, create default track
            track_name = "General Track"
            strand_name = name

        # Generate codes
        track_code = "".join(word[0] for word in track_name.split()[:4]).upper()
        strand_code = "".join(word[0] for word in strand_name.split()[:4]).upper()

        # Get or create track
        track, _ = Track.objects.get_or_create(
            code=track_code, defaults={"name": track_name, "level_type": level_type}
        )

        # Get or create strand
        strand, created = Strand.objects.get_or_create(
            track=track, code=strand_code, defaults={"name": strand_name}
        )

        return strand


class CourseSerializer(serializers.ModelSerializer):
    """Full serializer for courses with student count"""

    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "code",
            "abbreviation",
            "description",
            "level_type",
            "duration_years",
            "student_count",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_student_count(self, obj):
        return obj.students.count()


class CourseListSerializer(serializers.ModelSerializer):
    """Simplified serializer for course lists/dropdowns"""

    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "code",
            "abbreviation",
            "level_type",
            "duration_years",
            "is_active",
        ]


class SectionSerializer(serializers.ModelSerializer):
    """Full serializer for sections"""

    display_name = serializers.SerializerMethodField()
    strand_name = serializers.CharField(source="strand.name", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)
    adviser_name = serializers.CharField(source="adviser.full_name", read_only=True)

    class Meta:
        model = Section
        fields = [
            "id",
            "name",
            "level_type",
            "grade_year",
            "display_name",
            "strand",
            "strand_name",
            "course",
            "course_name",
            "adviser",
            "adviser_name",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_display_name(self, obj):
        grade = f" - {obj.grade_year}" if obj.grade_year else ""
        return f"{obj.name}{grade}"


class SectionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for section lists/dropdowns"""

    display_name = serializers.SerializerMethodField()
    strand_name = serializers.CharField(source="strand.name", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)
    adviser_name = serializers.CharField(source="adviser.full_name", read_only=True)

    class Meta:
        model = Section
        fields = [
            "id",
            "name",
            "level_type",
            "grade_year",
            "display_name",
            "strand",
            "strand_name",
            "course",
            "course_name",
            "adviser",
            "adviser_name",
            "is_active",
        ]

    def get_display_name(self, obj):
        grade = f" - {obj.grade_year}" if obj.grade_year else ""
        return f"{obj.name}{grade}"
