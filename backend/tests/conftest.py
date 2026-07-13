"""Fixtures compartilhadas dos testes de contrato/integração."""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def user(db):
    return User.objects.create(auth_id=uuid.uuid4(), email="aluno@example.com")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def note_type(db):
    from apps.notes.models import NoteType

    return NoteType.objects.create(
        name="Básico",
        field_names=["Frente", "Verso"],
        templates=[{"name": "Card 1"}],
    )


@pytest.fixture
def make_deck(note_type):
    from apps.catalog.models import Deck

    def _make(**kwargs):
        kwargs.setdefault("name", "Deck Teste")
        kwargs.setdefault("subject_tags", [])
        return Deck.objects.create(note_type=note_type, **kwargs)

    return _make
