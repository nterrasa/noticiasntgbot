"""Lectura/escritura del estado persistente en state.json.

state.json guarda:
  - offset: ultimo update_id de Telegram ya procesado + 1 (para getUpdates)
  - last_summary_date: fecha (YYYY-MM-DD, hora Madrid) del ultimo resumen enviado
  - sent: {id_noticia: fecha_iso} para no repetir noticias ya enviadas

El commit de este archivo lo hace el workflow de GitHub Actions cuando cambia.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import config

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

_DEFAULT = {"offset": 0, "last_summary_date": "", "sent": {}}


def load():
    """Devuelve el estado; si el archivo no existe o esta corrupto, valores por defecto."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULT)
    # asegurar que existen todas las claves
    for k, v in _DEFAULT.items():
        data.setdefault(k, v if not isinstance(v, dict) else {})
    return data


def save(state):
    """Guarda el estado en disco (con orden estable para diffs de git limpios)."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def prune_sent(state):
    """Elimina noticias enviadas hace mas de SENT_TTL_DAYS para no crecer sin fin."""
    limit = datetime.now(timezone.utc) - timedelta(days=config.SENT_TTL_DAYS)
    sent = state.get("sent", {})
    kept = {}
    for item_id, iso in sent.items():
        try:
            when = datetime.fromisoformat(iso)
        except ValueError:
            continue  # entrada rara -> se descarta
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when >= limit:
            kept[item_id] = iso
    state["sent"] = kept


def mark_sent(state, item_id):
    """Marca una noticia como ya enviada (ahora, en UTC)."""
    state["sent"][item_id] = datetime.now(timezone.utc).isoformat()


def is_sent(state, item_id):
    return item_id in state.get("sent", {})
