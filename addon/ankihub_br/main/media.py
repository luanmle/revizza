"""Sincronização de mídia com dedup por hash de conteúdo (FR-036)."""

import hashlib
from pathlib import Path


def sync_media(col, media_items: list[dict], client) -> int:
    """Baixa só o que está ausente ou com hash divergente; retorna o nº baixado."""
    media_dir = Path(col.media.dir())
    downloaded = 0
    for item in media_items:
        target = media_dir / item["filename"]
        if (
            target.exists()
            and hashlib.sha256(target.read_bytes()).hexdigest() == item["content_hash"]
        ):
            continue  # inalterado — não rebaixar (FR-036)
        url = client.get_media_url(item["content_hash"])
        target.write_bytes(client.download_file(url))
        downloaded += 1
    return downloaded
