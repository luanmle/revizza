from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Deck
from apps.notes.views import _require_subscription

from .models import ProtectedFieldConfig, ProtectedTagConfig
from .serializers import ProtectionConfigSerializer


class ProtectionMeView(APIView):
    """GET/PUT /decks/{id}/protection/me/ — configuração privada (FR-040)."""

    def get_deck(self, request, deck_id):
        deck = get_object_or_404(Deck.objects.select_related("note_type"), pk=deck_id)
        _require_subscription(request.user, deck)
        return deck

    def get(self, request, deck_id):
        deck = self.get_deck(request, deck_id)
        fields = list(
            ProtectedFieldConfig.objects.filter(user=request.user, deck=deck)
            .order_by("created_at", "id")
            .values_list("field_name", flat=True)
        )
        tags = list(
            ProtectedTagConfig.objects.filter(user=request.user, deck=deck)
            .order_by("created_at", "id")
            .values_list("tag", flat=True)
        )
        return Response({"fields": fields, "tags": tags})

    def put(self, request, deck_id):
        deck = self.get_deck(request, deck_id)
        serializer = ProtectionConfigSerializer(
            data=request.data, context={"deck": deck}
        )
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data["fields"]
        tags = serializer.validated_data["tags"]
        with transaction.atomic():
            ProtectedFieldConfig.objects.filter(user=request.user, deck=deck).delete()
            ProtectedTagConfig.objects.filter(user=request.user, deck=deck).delete()
            ProtectedFieldConfig.objects.bulk_create(
                ProtectedFieldConfig(user=request.user, deck=deck, field_name=field)
                for field in fields
            )
            ProtectedTagConfig.objects.bulk_create(
                ProtectedTagConfig(user=request.user, deck=deck, tag=tag)
                for tag in tags
            )
        return Response({"fields": fields, "tags": tags})
