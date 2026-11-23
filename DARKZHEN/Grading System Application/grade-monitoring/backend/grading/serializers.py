from rest_framework import serializers

from .models import Assessment, GradingConfig


class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = [
            "id",
            "class_assignment",
            "component",
            "quarter",
            "title",
            "highest_possible_score",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"class_assignment": {"required": False}}

    def validate_highest_possible_score(self, value):
        if value <= 0:
            raise serializers.ValidationError("Highest possible score must be greater than zero.")
        return value


class ScoreEntrySerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    raw = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True, required=False)


class BulkScoresSerializer(serializers.Serializer):
    scores = serializers.ListField(child=ScoreEntrySerializer(), allow_empty=True)


class GradingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingConfig
        fields = ["id", "name", "weights", "transmutation_table", "is_active", "updated_at"]
        read_only_fields = ["id", "updated_at"]
