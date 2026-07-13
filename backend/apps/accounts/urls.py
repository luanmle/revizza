from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view()),
    path("password-reset/", views.PasswordResetView.as_view()),
    path("me/", views.MeView.as_view()),
    path("me/consents/", views.ConsentsView.as_view()),
    path("me/deletion-request/", views.DeletionRequestView.as_view()),
    path("me/export/", views.DataExportView.as_view()),
]
