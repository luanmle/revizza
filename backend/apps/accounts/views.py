from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import supabase_gateway
from .models import User
from .serializers import ConsentsSerializer, RegisterSerializer, UserSerializer


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
            supabase_gateway.send_password_reset(email)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET /accounts/me/ — perfil, preferências e consentimentos (FR-002)."""

    def get(self, request):
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
