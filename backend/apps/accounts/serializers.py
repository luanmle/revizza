from rest_framework import serializers

from . import avatars
from .models import User

PROFILE_FIELDS = [
    "id",
    "name",
    "email",
    "avatar_url",
    "target_career",
    "target_board",
    "consent_marketing_emails",
    "consent_research_data",
    "deletion_requested_at",
    "created_at",
]


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = PROFILE_FIELDS
        read_only_fields = PROFILE_FIELDS

    def get_avatar_url(self, user):
        return avatars.public_url(user.avatar_path)


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    target_career = serializers.ChoiceField(
        choices=User.TargetCareer.choices, required=False, allow_null=True
    )
    target_board = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )
    # FR-005: os dois consentimentos são opt-in, nunca pré-marcados
    consent_marketing_emails = serializers.BooleanField(default=False)
    consent_research_data = serializers.BooleanField(default=False)


class ConsentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["consent_marketing_emails", "consent_research_data"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """PATCH /accounts/me/ — campos texto (avatar é tratado à parte em MeView.patch,
    pois exige acesso a request.FILES e semântica própria de remoção)."""

    class Meta:
        model = User
        fields = ["name", "target_career", "target_board"]
