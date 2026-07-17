"""Sincronização de mídia com dedup por hash de conteúdo (FR-036).

Pipeline em duas fases (research.md §2, §3):
- stage_media: valida e materializa cada mídia numa área de staging temporária,
  com nome de arquivo derivado do hash (determinístico por conteúdo);
- commit_media: escreve o que foi validado na pasta de mídia do Anki via
  col.media.write_data (nunca Path.write_bytes — path-safe + rename-on-collision).

Uma mídia que falha na validação simplesmente não entra no mapa retornado; a
nota que a referencia mantém o <img src> intacto (F1 / research.md §9).
"""

import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from ..ankihub_br_client.client import MEDIA_MAX_BYTES, MediaTooLarge
from .constants import MEDIA_CONCURRENCY_DEFAULT

__all__ = [
    "MEDIA_MAX_BYTES",
    "StagedMedia",
    "commit_media",
    "media_staging_dir",
    "stage_media",
]

# TTL folgado: qualquer arquivo de staging mais velho que isso é órfão de um run
# que não terminou de limpar (uma execução completa sempre remove o que criou).
STAGING_TTL_SECONDS = 24 * 60 * 60


@dataclass
class StagedMedia:
    content_hash: str
    resolved_filename: str
    staging_path: Path | None  # None = já presente localmente, nada a escrever
    byte_size: int


def media_staging_dir() -> Path:
    staging_dir = Path(__file__).resolve().parents[1] / "user_files" / "media_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    return staging_dir


def _resolved_filename(content_hash: str, original_filename: str) -> str:
    """Nome local determinístico: <hash>.<ext> (research.md §2)."""
    ext = os.path.splitext(original_filename)[1].lstrip(".")
    ext = "".join(c for c in ext if c.isalnum())  # descarta extensão suspeita
    return f"{content_hash}.{ext}" if ext else content_hash


def _sweep_stale(staging_dir: Path) -> None:
    """FR-015: remove arquivos de staging órfãos de runs anteriores."""
    cutoff = time.time() - STAGING_TTL_SECONDS
    for entry in staging_dir.iterdir():
        if entry.is_file() and entry.stat().st_mtime < cutoff:
            entry.unlink(missing_ok=True)


def _validate(data: bytes, content_hash: str) -> bool:
    return (
        len(data) <= MEDIA_MAX_BYTES
        and hashlib.sha256(data).hexdigest() == content_hash
    )


def _download_one(client, content_hash: str, resolved: str, staging_dir: Path):
    """Baixa+valida um item (sem tocar em `col`): seguro para rodar em thread."""
    try:
        url = client.get_media_url(content_hash)
        data = client.download_file(url)
    except MediaTooLarge:
        return None  # oversized: descartado, item ausente do mapa
    except Exception:
        return None  # rede/validação: nota fica com <img src> não resolvido (F1)
    if not _validate(data, content_hash):
        return None
    # grava num temp e só então renomeia para o nome resolvido: um download
    # truncado nunca fica acessível sob o nome final de staging (FR-014)
    cached = staging_dir / resolved
    tmp = staging_dir / f".{content_hash}.part"
    tmp.write_bytes(data)
    os.replace(tmp, cached)
    return StagedMedia(content_hash, resolved, cached, len(data))


def stage_media(
    col,
    media_items: list[dict],
    client,
    staging_dir: Path,
    *,
    concurrency: int = MEDIA_CONCURRENCY_DEFAULT,
    should_cancel=None,
    on_progress=None,
) -> list:
    """Baixa/valida cada mídia ausente; retorna os itens disponíveis localmente.

    Ordem de skip (FR-008/FR-013):
    1. já commitada (`col.media.have`) → nenhum download, sem staging;
    2. já validada e em staging de um run anterior → reusa os bytes;
    3. caso contrário baixa (stream, com cap), valida SHA-256 + tamanho.
    Item que falha na validação é omitido (mapa parcial, research.md §9).

    Downloads da fase 3 rodam em paralelo (limite `concurrency`, FR-019). Se
    `should_cancel()` fica verdadeiro nenhum novo download é submetido; os temps
    em voo são descartados, os já commitados ficam (FR-021).
    """
    _sweep_stale(staging_dir)
    staged: list[StagedMedia] = []
    to_download: list[tuple[str, str]] = []  # (content_hash, resolved)
    for item in media_items:
        content_hash = item["content_hash"]
        resolved = _resolved_filename(content_hash, item["filename"])

        if col.media.have(resolved):  # já escrito num run anterior — reaproveita
            staged.append(StagedMedia(content_hash, resolved, None, 0))
            continue

        cached = staging_dir / resolved
        if cached.exists():
            data = cached.read_bytes()
            if _validate(data, content_hash):  # revalida antes de reusar
                staged.append(StagedMedia(content_hash, resolved, cached, len(data)))
                continue
            cached.unlink(missing_ok=True)  # staging corrompido → rebaixa

        to_download.append((content_hash, resolved))

    total = len(media_items)
    processed = len(staged)  # itens já resolvidos por skip (have/cache)
    if on_progress:
        on_progress(processed, total)
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = []
        for content_hash, resolved in to_download:
            if should_cancel and should_cancel():
                break  # cancelamento: para de submeter novos downloads (FR-021)
            futures.append(
                pool.submit(_download_one, client, content_hash, resolved, staging_dir)
            )
        for future in futures:
            result = future.result()
            processed += 1
            if result is not None:
                staged.append(result)
            if on_progress:
                on_progress(processed, total)
    return staged


def commit_media(col, staged_items: list) -> dict:
    """Escreve o staging validado na pasta de mídia; retorna hash → nome final."""
    resolved_map: dict[str, str] = {}
    for item in staged_items:
        if item.staging_path is None:  # já presente localmente
            resolved_map[item.content_hash] = item.resolved_filename
            continue
        data = item.staging_path.read_bytes()
        # write_data resolve dentro da pasta de mídia (path-safe) e renomeia em
        # colisão de nome — nunca sobrescreve (research.md §1)
        final_name = col.media.write_data(item.resolved_filename, data)
        item.staging_path.unlink(missing_ok=True)
        resolved_map[item.content_hash] = final_name
    return resolved_map
