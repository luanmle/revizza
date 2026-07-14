from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import supabase_gateway
from .models import User
from .serializers import (
    ConsentsSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    """POST /accounts/register/ — cria conta no Supabase Auth + perfil local (FR-001)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            auth_id = supabase_gateway.sign_up(data["email"], data["password"])
        except Exception as exc:  # e-mail já usado, senha rejeitada etc.
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create(
            auth_id=auth_id,
            name=data.get("name", "").strip(),
            email=data["email"],
            target_career=data.get("target_career"),
            target_board=data.get("target_board") or None,
            consent_marketing_emails=data["consent_marketing_emails"],
            consent_research_data=data["consent_research_data"],
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class PasswordResetView(APIView):
    """POST /accounts/password-reset/ — delega ao Supabase Auth (FR-003)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "")
        if email:
            # 204 sempre — não revela se o e-mail existe
            supabase_gateway.send_password_reset(
                email, settings.PASSWORD_RESET_REDIRECT_URL
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET /accounts/me/ — perfil, preferências e consentimentos (FR-002)."""

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            instance=request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ConsentsView(APIView):
    """PATCH /accounts/me/consents/ — efeito imediato (FR-005, FR-045)."""

    def patch(self, request):
        serializer = ConsentsSerializer(
            instance=request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DeletionRequestView(APIView):
    """Agenda/cancela exclusão com carência de sete dias (FR-046)."""

    grace_period = timedelta(days=7)

    def post(self, request):
        if request.user.deletion_requested_at is None:
            request.user.deletion_requested_at = timezone.now()
            request.user.save(update_fields=["deletion_requested_at", "updated_at"])
        return Response(
            {
                "requested_at": request.user.deletion_requested_at,
                "scheduled_for": request.user.deletion_requested_at + self.grace_period,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    def delete(self, request):
        requested_at = request.user.deletion_requested_at
        if requested_at is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        if timezone.now() >= requested_at + self.grace_period:
            return Response(
                {
                    "detail": "A carência terminou; a exclusão não pode mais ser cancelada."
                },
                status=status.HTTP_409_CONFLICT,
            )
        request.user.deletion_requested_at = None
        request.user.save(update_fields=["deletion_requested_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class DataExportView(APIView):
    """Exporta dados pessoais e conteúdo autoral em JSON (FR-047)."""

    def get(self, request):
        profile = UserSerializer(request.user).data
        profile["deletion_requested_at"] = request.user.deletion_requested_at
        suggestions = list(
            request.user.suggestions.order_by("created_at").values(
                "id",
                "deck_id",
                "type",
                "status",
                "change_category",
                "justification",
                "proposed_field_values",
                "proposed_tags",
                "rejection_reason",
                "created_at",
                "updated_at",
            )
        )
        comments = list(
            request.user.comments.order_by("created_at").values(
                "id",
                "note_id",
                "suggestion_id",
                "body",
                "created_at",
                "edited_at",
            )
        )
        return Response(
            {
                "generated_at": timezone.now(),
                "profile": profile,
                "suggestions": suggestions,
                "comments": comments,
            }
        )
