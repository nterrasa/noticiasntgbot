"""Bot de noticias de Telegram sobre GitHub Actions (sin servidor).

En cada ejecucion (cron cada 5 min) hace dos cosas:
  1) Lee comandos/botones nuevos con getUpdates y responde (solo a CHAT_ID).
  2) Si son ~las 09:00 de Madrid y hoy aun no se envio el resumen, lo envia.

El token y el chat_id se leen SIEMPRE de variables de entorno (GitHub Secrets):
  BOT_TOKEN, CHAT_ID.  Nunca se escriben en el codigo.
"""

import os
import sys
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9 (no deberia pasar en Actions)
    ZoneInfo = None

import config
import news
import state as state_mod
import tg


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Textos del bot (en espanol)
# ---------------------------------------------------------------------------
HELP_TEXT = (
    "\U0001F44B <b>Bot de Noticias</b>\n\n"
    "Cada manana a las 09:00 (hora de Madrid) te mando un resumen con las "
    "novedades de cada sector y botones para leer las noticias.\n\n"
    "Tambien puedes pedirme noticias cuando quieras con estos comandos:\n"
    "\U0001F69C /granjas — Granjas y farming (UK e Irlanda)\n"
    "\U0001F33E /agricola — Agricola (España y Cataluña)\n"
    "\U0001F3AC /cine — Cine, audiovisual, marketing y motion\n"
    "\U0001F697 /coches — Coches\n"
    "\U0001F4F0 /todo — Un poco de todas las categorias\n"
    "ℹ️ /ayuda — Ver esta ayuda\n\n"
    "<i>Nota: como el bot es gratuito y se ejecuta cada 5 minutos, puede "
    "tardar hasta ~5 min en responderte. Las noticias de UK/Irlanda salen en "
    "su idioma original.</i>"
)

_WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _spanish_date(dt):
    return f"{_WEEKDAYS[dt.weekday()]}, {dt.day} de {_MONTHS[dt.month - 1]} de {dt.year}"


# ---------------------------------------------------------------------------
# Envio de noticias de una categoria
# ---------------------------------------------------------------------------
def deliver_category(cat_key, state, token, chat_id, todo=False, silent_if_empty=False):
    """Envia las noticias de una categoria (un mensaje por noticia). Devuelve nº enviadas."""
    cat = config.CATEGORIES[cat_key]
    max_items = config.MAX_PER_CATEGORY_TODO if todo else config.MAX_PER_CATEGORY
    items = news.get_category_items(cat_key, max_items, state["sent"])

    header = f"{cat['emoji']} <b>{cat['title']}</b>"
    if not items:
        if not silent_if_empty:
            tg.send_message(token, chat_id,
                            f"{header}\nNo hay noticias nuevas ahora mismo.",
                            disable_preview=True)
        return 0

    tg.send_message(token, chat_id, f"{header} — últimas noticias",
                    disable_preview=True)
    for item in items:
        tg.send_message(token, chat_id, news.format_item(item))
        state_mod.mark_sent(state, item.id)
    return len(items)


def deliver_all(state, token, chat_id):
    """Comando /todo: unas pocas noticias de cada categoria."""
    tg.send_message(token, chat_id, "\U0001F4F0 <b>Un poco de todo</b>",
                    disable_preview=True)
    total = 0
    for cat_key in config.CATEGORY_ORDER:
        total += deliver_category(cat_key, state, token, chat_id,
                                  todo=True, silent_if_empty=True)
    if total == 0:
        tg.send_message(token, chat_id,
                        "No hay noticias nuevas en ninguna categoria ahora mismo.",
                        disable_preview=True)


# ---------------------------------------------------------------------------
# Resumen de la manana
# ---------------------------------------------------------------------------
def _morning_keyboard():
    def btn(key):
        c = config.CATEGORIES[key]
        return {"text": f"{c['emoji']} {c['title'].split(' (')[0]}",
                "callback_data": f"cat:{key}"}
    return {
        "inline_keyboard": [
            [btn("granjas"), btn("agricola")],
            [btn("cine"), btn("coches")],
            [{"text": "\U0001F4F0 Ver todo", "callback_data": "cat:todo"}],
        ]
    }


def send_morning(state, token, chat_id, now_madrid):
    """Un mensaje de buenos dias con teaser por sector + botones para leer."""
    lines = [
        "\U0001F305 <b>Buenos días</b>",
        f"\U0001F4C5 {_spanish_date(now_madrid)}",
        "",
        "Novedades por sector:",
    ]
    for cat_key in config.CATEGORY_ORDER:
        cat = config.CATEGORIES[cat_key]
        items = news.get_category_items(
            cat_key, 10, state["sent"], fresh_hours=config.MORNING_FRESH_HOURS
        )
        short_title = cat["title"].split(" (")[0]
        if items:
            top = items[0].title
            if len(top) > 90:
                top = top[:90].rstrip() + "…"
            lines.append(
                f"{cat['emoji']} <b>{short_title}</b>: {len(items)} "
                f"{'novedad' if len(items) == 1 else 'novedades'}"
            )
            lines.append(f"   · <i>{news.esc(top)}</i>")
        else:
            lines.append(f"{cat['emoji']} <b>{short_title}</b>: sin novedades")
    lines.append("")
    lines.append("Pulsa un botón para leer las noticias \U0001F447")

    tg.send_message(token, chat_id, "\n".join(lines),
                    reply_markup=_morning_keyboard(), disable_preview=True)


# ---------------------------------------------------------------------------
# Procesado de un update
# ---------------------------------------------------------------------------
def handle_update(update, state, token, chat_id):
    # --- Botones (callback_query) ---
    if "callback_query" in update:
        cq = update["callback_query"]
        from_id = str(cq.get("from", {}).get("id", ""))
        tg.answer_callback(token, cq["id"])
        if from_id != str(chat_id):
            return  # ignorar a desconocidos
        data = cq.get("data", "")
        if data == "cat:todo":
            deliver_all(state, token, chat_id)
        elif data.startswith("cat:"):
            key = data.split(":", 1)[1]
            if key in config.CATEGORIES:
                deliver_category(key, state, token, chat_id)
        return

    # --- Mensajes de texto ---
    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    if str(message.get("chat", {}).get("id", "")) != str(chat_id):
        return  # solo atendemos a nuestro chat_id
    text = (message.get("text") or "").strip()
    if not text.startswith("/"):
        tg.send_message(token, chat_id,
                        "No te he entendido. Escribe /ayuda para ver los comandos.",
                        disable_preview=True)
        return

    cmd = text.split()[0].lstrip("/").split("@")[0].lower()
    if cmd in ("start", "ayuda", "help"):
        tg.send_message(token, chat_id, HELP_TEXT, disable_preview=True)
    elif cmd == "todo":
        deliver_all(state, token, chat_id)
    elif cmd in config.CATEGORIES:
        deliver_category(cmd, state, token, chat_id)
    else:
        tg.send_message(token, chat_id,
                        "Comando no reconocido. Escribe /ayuda.",
                        disable_preview=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id:
        log("ERROR: faltan las variables de entorno BOT_TOKEN y/o CHAT_ID.")
        sys.exit(1)

    state = state_mod.load()
    state_mod.prune_sent(state)

    # 1) Comandos y botones nuevos
    updates = tg.get_updates(token, state["offset"])
    for update in updates:
        state["offset"] = update["update_id"] + 1
        try:
            handle_update(update, state, token, chat_id)
        except Exception as exc:  # un update roto no debe tumbar el resto
            log(f"[bot] error procesando update {update.get('update_id')}: {exc}")

    # 2) Resumen de la manana (09:00 Madrid, una vez al dia)
    tz = ZoneInfo(config.TIMEZONE) if ZoneInfo else None
    now_madrid = datetime.now(tz)
    today = now_madrid.strftime("%Y-%m-%d")
    force = os.environ.get("FORCE_MORNING") == "1"
    in_window = config.SEND_HOUR <= now_madrid.hour < config.SEND_WINDOW_END_HOUR
    if force or (state.get("last_summary_date") != today and in_window):
        log(f"[bot] enviando resumen de la manana (force={force})")
        try:
            send_morning(state, token, chat_id, now_madrid)
            if not force:  # en modo test no marcamos, para no bloquear el real
                state["last_summary_date"] = today
        except Exception as exc:
            log(f"[bot] error enviando el resumen: {exc}")

    state_mod.save(state)
    log(f"[bot] listo. updates={len(updates)} offset={state['offset']} "
        f"sent_cache={len(state['sent'])}")


if __name__ == "__main__":
    main()
