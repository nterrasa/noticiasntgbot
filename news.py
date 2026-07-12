"""Descarga de feeds RSS, limpieza, deduplicacion y formato de noticias."""

import hashlib
import html
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser
import requests

import config


def log(msg):
    print(msg, file=sys.stderr, flush=True)


@dataclass
class Item:
    id: str
    title: str
    link: str
    summary: str
    source_name: str
    source_type: str        # "rss" | "gnews"
    published: datetime     # siempre timezone-aware (UTC); epoch si desconocido


# ---------------------------------------------------------------------------
# Limpieza de texto
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean_html(text):
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _truncate(text, limit=280):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # cortar en el ultimo espacio para no partir palabras
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" .,;:") + "…"  # ...


def _strip_publisher(title):
    """Google News anade ' - Editorial' al final del titular. Lo separamos."""
    if " - " in title:
        base, publisher = title.rsplit(" - ", 1)
        # heuristica: la editorial no suele tener mas de 6 palabras
        if base and len(publisher.split()) <= 6:
            return base.strip(), publisher.strip()
    return title, ""


# ---------------------------------------------------------------------------
# Fecha
# ---------------------------------------------------------------------------
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _parse_date(entry):
    for attr in ("published_parsed", "updated_parsed"):
        st = getattr(entry, attr, None)
        if st:
            try:
                return datetime(*st[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass
    return None


# ---------------------------------------------------------------------------
# Identidad para deduplicar
# ---------------------------------------------------------------------------
def _item_id(link, guid):
    base = (guid or link or "").strip().lower()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def _norm_title(title):
    return _WS_RE.sub(" ", title.lower()).strip()


# ---------------------------------------------------------------------------
# Descarga de una fuente
# ---------------------------------------------------------------------------
def fetch_source(source):
    """Devuelve una lista de Item de una fuente. Nunca lanza: si falla, [] ."""
    url = source["url"]
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            },
            timeout=config.HTTP_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log(f"[news] fallo al descargar {source['name']}: {exc}")
        return []

    feed = feedparser.parse(resp.content)
    items = []
    for entry in feed.entries[: config.MAX_PER_SOURCE]:
        title = _clean_html(getattr(entry, "title", "")) or "(sin titulo)"
        link = getattr(entry, "link", "") or ""
        if not link:
            continue
        guid = getattr(entry, "id", "") or getattr(entry, "guid", "")
        published = _parse_date(entry) or _EPOCH

        if source["type"] == "gnews":
            title, _publisher = _strip_publisher(title)
            summary = ""  # Google News no da descripcion util (solo un enlace)
        else:
            raw = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary = _truncate(_clean_html(raw))

        items.append(
            Item(
                id=_item_id(link, guid),
                title=title,
                link=link,
                summary=summary,
                source_name=source["name"],
                source_type=source["type"],
                published=published,
            )
        )
    return items


# ---------------------------------------------------------------------------
# Agregacion por categoria
# ---------------------------------------------------------------------------
def get_category_items(cat_key, max_items, sent_ids, fresh_hours=None):
    """Noticias de una categoria: mas recientes, sin duplicados, no ya enviadas.

    - sent_ids: conjunto de ids ya enviados (se excluyen).
    - fresh_hours: si se indica, solo items publicados en esas ultimas horas.
    """
    cat = config.CATEGORIES[cat_key]
    now = datetime.now(timezone.utc)
    max_age = now.timestamp() - config.MAX_AGE_DAYS * 86400

    collected = []
    for source in cat["sources"]:
        collected.extend(fetch_source(source))

    seen_ids = set()
    seen_titles = set()
    result = []
    # mas nuevo primero
    for item in sorted(collected, key=lambda i: i.published, reverse=True):
        if item.id in sent_ids or item.id in seen_ids:
            continue
        norm = _norm_title(item.title)
        if norm in seen_titles:
            continue  # misma noticia en dos fuentes distintas
        # descartar demasiado viejo (salvo fecha desconocida = epoch)
        if item.published != _EPOCH and item.published.timestamp() < max_age:
            continue
        if fresh_hours is not None:
            if item.published == _EPOCH:
                continue
            age_h = (now - item.published).total_seconds() / 3600
            if age_h > fresh_hours:
                continue
        seen_ids.add(item.id)
        seen_titles.add(norm)
        result.append(item)
        if len(result) >= max_items:
            break
    return result


# ---------------------------------------------------------------------------
# Formato para Telegram (HTML)
# ---------------------------------------------------------------------------
def esc(text):
    """Escapa solo lo imprescindible para el modo HTML de Telegram (< > &)."""
    return html.escape(text, quote=False)


def format_item(item):
    """Un mensaje por noticia: titular en negrita + frases + enlace."""
    title = esc(item.title)
    if item.source_type == "gnews":
        link = html.escape(item.link, quote=True)  # va en atributo href
        return (
            f"<b>{title}</b>\n"
            f"<i>Fuente: {esc(item.source_name)}</i>\n"
            f'<a href="{link}">\U0001F517 Abrir noticia</a>'
        )
    # feed nativo: enlace visible para que Telegram muestre la vista previa
    parts = [f"<b>{title}</b>"]
    if item.summary:
        parts.append(esc(item.summary))
    parts.append(esc(item.link))
    parts.append(f"<i>{esc(item.source_name)}</i>")
    return "\n".join(parts)
