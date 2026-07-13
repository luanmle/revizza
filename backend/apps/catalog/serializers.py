from rest_framework import serializers

from .models import Deck, Subscription


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

    class Meta(DeckSerializer.Meta):
        fields = DeckSerializer.Meta.fields + ["moderators", "is_subscribed"]

    def get_moderators(self, deck):
        return [
            {"id": str(m.user_id), "email": m.user.email}
            for m in deck.moderators.filter(status="active").select_related("user")
        ]

    def get_is_subscribed(self, deck):
        user = self.context["request"].user
        return deck.subscriptions.filter(user=user).exists()


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
