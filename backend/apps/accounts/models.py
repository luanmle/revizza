from django.db import models

from apps.base import BaseModel


class User(BaseModel):
    """Perfil do produto por trás do usuário do Supabase Auth (data-model.md)."""

    class TargetCareer(models.TextChoices):
        FISCAL = "fiscal"
        POLICIAL = "policial"
        JURIDICA = "juridica"
        OUTRA = "outra"

    auth_id = models.UUIDField(unique=True)
    email = models.EmailField()
    target_career = models.CharField(
        max_length=16, choices=TargetCareer.choices, null=True, blank=True
    )
    target_board = models.CharField(max_length=120, null=True, blank=True)
    consent_marketing_emails = models.BooleanField(
        default=False
    )  # FR-005: nunca pré-marcado
    consent_research_data = models.BooleanField(
        default=False
    )  # FR-005: nunca pré-marcado
    is_suspended = models.BooleanField(default=False)  # FR-049: soft-ban reversível
    deletion_requested_at = models.DateTimeField(
        null=True, blank=True
    )  # FR-046: carência 7d

    # DRF espera request.user.is_authenticated; este modelo não herda de django.contrib.auth
    is_authenticated = True
    is_anonymous = False

    def __str__(self) -> str:
        return self.email
