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


@pytest.fixture
def make_note(make_deck):
    from django.utils import timezone

    from apps.notes.models import Note

    def _make(deck=None, **kwargs):
        deck = deck or make_deck()
        kwargs.setdefault("guid", uuid.uuid4().hex)
        kwargs.setdefault("field_values", {"Frente": "Pergunta", "Verso": "Resposta"})
        kwargs.setdefault("mod", timezone.now())
        return Note.objects.create(deck=deck, note_type=deck.note_type, **kwargs)

    return _make


@pytest.fixture
def subscribe(user):
    from apps.catalog.models import Subscription

    def _subscribe(deck):
        return Subscription.objects.get_or_create(user=user, deck=deck)[0]

    return _subscribe
