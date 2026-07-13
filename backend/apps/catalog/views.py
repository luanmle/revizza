import json

from django.db.models import Case, F, IntegerField, Q, TextField, Value, When
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.pagination import DefaultCursorPagination

from .models import Deck, Subscription
from .serializers import (
    DeckDetailSerializer,
    DeckSerializer,
    DeckSubscribedSerializer,
    SubscriptionSerializer,
)


def _json_escaped(text: str) -> str:
    """JSONField persiste não-ASCII escapado (\\u00ea); escapar a agulha igual."""
    return json.dumps(text, ensure_ascii=True)[1:-1]


class CatalogPagination(DefaultCursorPagination):
    # FR-008: recomendados no topo, depois mais assinantes/mais recentes
    ordering = ("-recommended", "-subscriber_count", "-created_at")


class DeckListView(generics.ListAPIView):
    pagination_class = CatalogPagination

    def get_serializer_class(self):
        if self.request.query_params.get("subscribed"):
            return DeckSubscribedSerializer
        return DeckSerializer

    def get_queryset(self):
        # ponytail: match textual no JSON das tags — funciona em sqlite e postgres;
        # trocar por jsonb containment se o catálogo crescer além do baseline do MVP
        qs = Deck.objects.annotate(tags_text=Cast("subject_tags", TextField()))

        if self.request.query_params.get("subscribed"):
            # consumido pelo add-on para saber o que sincronizar (FR-031)
            qs = qs.filter(subscriptions__user=self.request.user)

        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags_text__icontains=f'"{_json_escaped(tag)}"')  # FR-007

        user = self.request.user
        match = Q()
        if user.target_career:
            match |= Q(tags_text__icontains=_json_escaped(user.target_career))
        if user.target_board:
            match |= Q(tags_text__icontains=_json_escaped(user.target_board))
        if match:
            recommended = Case(
                When(match, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        else:
            recommended = Value(0, output_field=IntegerField())
        return qs.annotate(recommended=recommended)


class DeckDetailView(generics.RetrieveAPIView):
    queryset = Deck.objects.all()
    serializer_class = DeckDetailSerializer


class SubscriptionCreateView(APIView):
    """POST /decks/{id}/subscriptions/ — cria o vínculo de assinatura (FR-009)."""

    def post(self, request, deck_id):
        deck = get_object_or_404(Deck, pk=deck_id)
        serializer = SubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription, created = Subscription.objects.get_or_create(
            user=request.user, deck=deck, defaults=serializer.validated_data
        )
        if created:
            Deck.objects.filter(pk=deck.pk).update(
                subscriber_count=F("subscriber_count") + 1
            )
        return Response(
            SubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SubscriptionMeView(APIView):
    """PATCH/DELETE /decks/{id}/subscriptions/me/ — preferências e cancelamento."""

    def get_subscription(self, request, deck_id):
        return get_object_or_404(Subscription, user=request.user, deck_id=deck_id)

    def patch(self, request, deck_id):
        subscription = self.get_subscription(request, deck_id)
        serializer = SubscriptionSerializer(
            instance=subscription, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, deck_id):
        subscription = self.get_subscription(request, deck_id)
        subscription.delete()
        Deck.objects.filter(pk=deck_id).update(
            subscriber_count=F("subscriber_count") - 1
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
