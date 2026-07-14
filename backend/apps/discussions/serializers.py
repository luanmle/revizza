from rest_framework import serializers

from .models import Comment, Report


class CommentSerializer(serializers.ModelSerializer):
    """Comentário de thread (nota ou sugestão) — corpo texto puro (FR-024)."""

    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "author", "author_name", "body", "created_at", "edited_at"]
        read_only_fields = [
            "id",
            "author",
            "author_name",
            "created_at",
            "edited_at",
        ]

    def get_author_name(self, comment):
        return comment.author.name or None if comment.author else None


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "comment", "reason", "status", "created_at"]
        read_only_fields = ["id", "comment", "status", "created_at"]
