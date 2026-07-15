from django.db.models import Count
from rest_framework import serializers

from apps.accounts import avatars
from apps.notes.sanitize import sanitize_html

from .models import Deck, DeckModerator, Subscription
from .services import deck_sync_state


class DeckSerializer(serializers.ModelSerializer):
    creator = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    last_updated_at = serializers.DateTimeField(read_only=True)

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
            "last_updated_at",
            "is_official",
            "creator",
        ]

    def get_creator(self, deck):
        if not deck.creator:
            return None
        return {
            "id": str(deck.creator_id),
            "name": deck.creator.name,
            "avatar_url": avatars.public_url(deck.creator.avatar_path),
        }

    def get_description(self, deck):
        return sanitize_html(deck.description)


class DeckDetailSerializer(DeckSerializer):
    moderator_count = serializers.SerializerMethodField()
    is_moderator = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    note_types = serializers.SerializerMethodField()
    sync_status = serializers.SerializerMethodField()
    moderators = serializers.SerializerMethodField()

    class Meta(DeckSerializer.Meta):
        fields = DeckSerializer.Meta.fields + [
            "moderator_count",
            "is_moderator",
            "is_subscribed",
            "note_types",
            "sync_status",
            "moderators",
        ]

    def get_moderator_count(self, deck):
        return deck.moderators.filter(status=DeckModerator.Status.ACTIVE).count()

    def get_is_moderator(self, deck):
        return deck.moderators.filter(
            status=DeckModerator.Status.ACTIVE,
            user=self.context["request"].user,
        ).exists()

    def get_is_subscribed(self, deck):
        user = self.context["request"].user
        return deck.subscriptions.filter(user=user).exists()

    def get_sync_status(self, deck):
        return deck_sync_state(self.context["request"].user, deck)

    def get_moderators(self, deck):
        return [
            {
                "id": str(moderator.id),
                "user_id": str(moderator.user_id),
                "name": moderator.user.name,
                "avatar_url": avatars.public_url(moderator.user.avatar_path),
            }
            for moderator in deck.moderators.filter(
                status=DeckModerator.Status.ACTIVE
            ).select_related("user")
        ]

    def get_note_types(self, deck):
        # tipos derivados das notas vivas do deck, com contagem por tipo, em uma única
        # query agregada — sem N+1 (research.md Decisão 6)
        counts = (
            deck.notes.filter(deleted_at__isnull=True)
            .values("note_type", "note_type__name", "note_type__field_names")
            .annotate(note_count=Count("id"))
            .order_by("note_type__name")
        )
        return [
            {
                "id": str(row["note_type"]),
                "name": row["note_type__name"],
                "field_names": row["note_type__field_names"],
                "note_count": row["note_count"],
            }
            for row in counts
        ]


class DeckUpdateSerializer(serializers.Serializer):
    """PATCH /decks/{id}/ (contracts/decks-update.md, FR-002/003/005/007/008)."""

    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    subject_tags = serializers.ListField(
        child=serializers.CharField(allow_blank=True), required=False
    )

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("O título não pode ficar em branco.")
        return value

    def validate_description(self, value):
        return sanitize_html(value)

    def validate_subject_tags(self, value):
        deduped = []
        for tag in value:
            tag = tag.strip()
            if tag and tag not in deduped:
                deduped.append(tag)
        return deduped


class DeckSubscribedSerializer(DeckSerializer):
    """Listagem `?subscribed=1` consumida pelo add-on: inclui as prefs de sync."""

    subscription = serializers.SerializerMethodField()
    pending_sync = serializers.SerializerMethodField()

    class Meta(DeckSerializer.Meta):
        fields = DeckSerializer.Meta.fields + ["subscription", "pending_sync"]

    def get_subscription(self, deck):
        # ponytail: 1 query por deck; catálogo assinado é pequeno no MVP
        sub = deck.subscriptions.get(user=self.context["request"].user)
        return SubscriptionSerializer(sub).data

    def get_pending_sync(self, deck):
        return deck_sync_state(self.context["request"].user, deck) == "out_of_date"


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
    name = serializers.CharField(source="user.name", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = DeckModerator
        fields = [
            "id",
            "user_id",
            "email",
            "name",
            "avatar_url",
            "status",
            "created_at",
        ]
        read_only_fields = fields

    def get_avatar_url(self, moderator):
        return avatars.public_url(moderator.user.avatar_path)


class ModeratorInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
