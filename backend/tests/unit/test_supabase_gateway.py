from types import SimpleNamespace

from apps.accounts import supabase_gateway


def test_sign_up_passes_email_confirmation_redirect(monkeypatch, settings):
    credentials = {}
    settings.EMAIL_CONFIRMATION_REDIRECT_URL = "http://localhost:3000/verify-email"

    def sign_up(payload):
        credentials.update(payload)
        return SimpleNamespace(user=SimpleNamespace(id="auth-id"))

    monkeypatch.setattr(
        supabase_gateway,
        "_client",
        lambda: SimpleNamespace(auth=SimpleNamespace(sign_up=sign_up)),
    )

    assert supabase_gateway.sign_up("user@example.com", "password") == "auth-id"
    assert credentials == {
        "email": "user@example.com",
        "password": "password",
        "options": {"email_redirect_to": "http://localhost:3000/verify-email"},
    }
