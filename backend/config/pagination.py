from rest_framework.pagination import CursorPagination


class DefaultCursorPagination(CursorPagination):
    """Paginador default do projeto — campo `next`/`previous`, como o AnkiHub original."""

    ordering = "-created_at"
