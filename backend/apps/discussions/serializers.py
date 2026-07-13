from rest_framework import serializers

from .models import Comment, Report


class CommentSerializer(serializers.ModelSerializer):
    """Comentário de thread (nota ou sugestão) — corpo texto puro (FR-024)."""

    class Meta:
        model = Comment
        fields = ["id", "author", "body", "created_at", "edited_at"]
        read_only_fields = ["id", "author", "created_at", "edited_at"]


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "comment", "reason", "status", "created_at"]
        read_only_fields = ["id", "comment", "status", "created_at"]
