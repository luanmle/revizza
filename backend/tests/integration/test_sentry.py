import sentry_sdk
from django.http import HttpResponse
from django.test import override_settings
from django.urls import path
from sentry_sdk.transport import Transport


def _raise_test_error(_request):
    raise RuntimeError("falha sentry de teste")


urlpatterns = [
    path("_sentry-test/", _raise_test_error),
    path("_sentry-ok/", lambda _request: HttpResponse("ok")),
]


class CapturingTransport(Transport):
    def __init__(self):
        super().__init__({})
        self.events = []

    def capture_envelope(self, envelope):
        for item in envelope.items:
            if item.headers.get("type") == "event":
                self.events.append(item.payload.json)


@override_settings(ROOT_URLCONF=__name__)
def test_django_unhandled_error_reaches_sentry(client):
    transport = CapturingTransport()
    client.raise_request_exception = False
    scope = sentry_sdk.get_global_scope()
    previous_client = scope.client
    sentry_sdk.init(
        dsn="https://public@example.invalid/1",
        transport=transport,
        send_default_pii=False,
    )
    test_client = scope.client
    try:
        response = client.get("/_sentry-test/")
        sentry_sdk.flush()
    finally:
        scope.set_client(previous_client)
        test_client.close()

    assert response.status_code == 500
    assert any(
        value["type"] == "RuntimeError" and value["value"] == "falha sentry de teste"
        for event in transport.events
        for value in event["exception"]["values"]
    )
