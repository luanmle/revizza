from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    deck_id = serializers.UUIDField(read_only=True)
    deck_name = serializers.CharField(source="deck.name", read_only=True)
    suggestion_id = serializers.UUIDField(read_only=True)
    note_id = serializers.UUIDField(read_only=True)
    rejection_reason = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "deck_id",
            "deck_name",
            "suggestion_id",
            "note_id",
            "rejection_reason",
            "read_at",
            "created_at",
        ]

    def get_rejection_reason(self, obj: Notification) -> str | None:
        if obj.type != Notification.Type.SUGGESTION_REJECTED:
            return None
        return obj.suggestion.rejection_reason
