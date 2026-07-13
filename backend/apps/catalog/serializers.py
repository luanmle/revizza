from rest_framework import serializers

from .models import Deck, DeckModerator, Subscription


class DeckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = [
            "id",
            "name",
            "description",
            "subject_tags",
            "note_count",
            "subscriber_count",
            "created_at",
        ]


class DeckDetailSerializer(DeckSerializer):
    moderators = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    note_type = serializers.SerializerMethodField()

    class Meta(DeckSerializer.Meta):
        fields = DeckSerializer.Meta.fields + [
            "moderators",
            "is_subscribed",
            "note_type",
        ]

    def get_moderators(self, deck):
        return [
            {"id": str(m.user_id), "email": m.user.email}
            for m in deck.moderators.filter(status="active").select_related("user")
        ]

    def get_is_subscribed(self, deck):
        user = self.context["request"].user
        return deck.subscriptions.filter(user=user).exists()

    def get_note_type(self, deck):
        return {
            "id": str(deck.note_type_id),
            "name": deck.note_type.name,
            "field_names": deck.note_type.field_names,
        }


class DeckSubscribedSerializer(DeckSerializer):
    """Listagem `?subscribed=1` consumida pelo add-on: inclui as prefs de sync."""

    subscription = serializers.SerializerMethodField()

    class Meta(DeckSerializer.Meta):
        fields = DeckSerializer.Meta.fields + ["subscription"]

    def get_subscription(self, deck):
        # ponytail: 1 query por deck; catálogo assinado é pequeno no MVP
        sub = deck.subscriptions.get(user=self.context["request"].user)
        return SubscriptionSerializer(sub).data


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "deck",
            "sync_trigger_manual",
            "sync_trigger_on_anki_open",
            "sync_trigger_chained_native",
            "delete_notes_on_removal",
        ]
        read_only_fields = ["deck"]


class DeckModeratorSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = DeckModerator
        fields = ["id", "user_id", "email", "status", "created_at"]
        read_only_fields = fields


class ModeratorInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
