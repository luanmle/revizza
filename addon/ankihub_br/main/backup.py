"""Backup pré-sync e reversão em falha (FR-033, FR-039).

Snapshot por cópia do arquivo com a coleção fechada — íntegro por construção.
"""

import shutil
from pathlib import Path

BACKUP_SUFFIX = ".ankihub_br_backup"


def create_backup(col) -> Path:
    """Fecha, copia e reabre a coleção; retorna o caminho do backup."""
    path = Path(col.path)
    backup_path = path.with_name(path.name + BACKUP_SUFFIX)
    col.close(downgrade=False)
    shutil.copy2(path, backup_path)
    col.reopen()
    return backup_path


def restore_backup(col, backup_path: Path) -> None:
    """Reverte a coleção para o backup pré-sync (FR-039) e reabre."""
    path = Path(col.path)
    col.close(downgrade=False)
    shutil.copy2(backup_path, path)
    col.reopen()
