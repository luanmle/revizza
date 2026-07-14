from rest_framework import serializers

from .models import User

PROFILE_FIELDS = [
    "id",
    "name",
    "email",
    "target_career",
    "target_board",
    "consent_marketing_emails",
    "consent_research_data",
    "deletion_requested_at",
    "created_at",
]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = PROFILE_FIELDS
        read_only_fields = PROFILE_FIELDS


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
    class Meta:
        model = User
        fields = ["name"]
