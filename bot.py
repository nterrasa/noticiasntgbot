"""Bot de noticias de Telegram sobre GitHub Actions (sin servidor).

En cada ejecucion (cron cada 5 min) hace dos cosas:
  1) Lee comandos/botones nuevos con getUpdates y responde (solo a CHAT_ID).
  2) Si son ~las 08:30 de Madrid y hoy aun no se envio el resumen, lo envia.

El token y el chat_id se leen SIEMPRE de variables de entorno (GitHub Secrets):
  BOT_TOKEN, CHAT_ID.  Nunca se escriben en el codigo.
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

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
    "\U0001f44b <b>Bot de Noticias</b>\n\n"
    "Cada manana a las 08:30 (hora de Madrid) te mando un resumen con las "
    "novedades de cada sector y botones para leer las noticias.\n\n"
    "Tambien puedes pedirme noticias cuando quieras con estos comandos:\n"
    "\U0001f69c /granjas — Granjas y farming (UK e Irlanda)\n"
    "\U0001f33e /agricola — Agricola (España y Cataluña)\n"
    "\U0001f3ac /cine — Cine, audiovisual, marketing y motion\n"
    "\U0001f697 /coches — Coches\n"
    "\U0001f4f0 /todo — Un poco de todas las categorias\n"
    "\U0001f4cb /resumen — Resumen de ahora (o el botón Resumen de abajo)\n"
    "ℹ️ /ayuda — Ver esta ayuda\n\n"
    "<i>Nota: como el bot es gratuito y se ejecuta cada 5 minutos, puede "
    "tardar hasta ~5 min en responderte. Las noticias de UK/Irlanda salen en "
    "su idioma original.</i>"
)

# Boton fijo bajo el teclado: al pulsarlo Telegram manda su texto como mensaje.
SUMMARY_BUTTON = "\U0001f4cb Resumen"
REPLY_KEYBOARD = {
    "keyboard": [[{"text": SUMMARY_BUTTON}]],
    "resize_keyboard": True,
    "is_persistent": True,
}

_WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MONTHS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def _spanish_date(dt):
    return (
        f"{_WEEKDAYS[dt.weekday()]}, {dt.day} de {_MONTHS[dt.month - 1]} de {dt.year}"
    )


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
            tg.send_message(
                token,
                chat_id,
                f"{header}\nNo hay noticias nuevas ahora mismo.",
                disable_preview=True,
            )
        return 0

    tg.send_message(
        token,
        chat_id,
        f"{header} — últimas noticias",
        reply_markup=REPLY_KEYBOARD,
        disable_preview=True,
    )
    for item in items:
        tg.send_message(token, chat_id, news.format_item(item))
        state_mod.mark_sent(state, item.id)
    return len(items)


def deliver_all(state, token, chat_id):
    """Comando /todo: unas pocas noticias de cada categoria."""
    tg.send_message(
        token,
        chat_id,
        "\U0001f4f0 <b>Un poco de todo</b>",
        reply_markup=REPLY_KEYBOARD,
        disable_preview=True,
    )
    total = 0
    for cat_key in config.CATEGORY_ORDER:
        total += deliver_category(
            cat_key, state, token, chat_id, todo=True, silent_if_empty=True
        )
    if total == 0:
        tg.send_message(
            token,
            chat_id,
            "No hay noticias nuevas en ninguna categoria ahora mismo.",
            disable_preview=True,
        )


# ---------------------------------------------------------------------------
# Resumen de la manana
# ---------------------------------------------------------------------------
def _morning_keyboard():
    def btn(key):
        c = config.CATEGORIES[key]
        return {
            "text": f"{c['emoji']} {c['title'].split(' (')[0]}",
            "callback_data": f"cat:{key}",
        }

    return {
        "inline_keyboard": [
            [btn("granjas"), btn("agricola")],
            [btn("cine"), btn("coches")],
            [{"text": "\U0001f4f0 Ver todo", "callback_data": "cat:todo"}],
        ]
    }


def send_morning(
    state, token, chat_id, now_madrid, title="\U0001f305 <b>Buenos días</b>"
):
    """Un mensaje (buenos dias o /resumen) con teaser por sector + botones para leer."""
    lines = [
        title,
        f"\U0001f4c5 {_spanish_date(now_madrid)}",
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
    lines.append("Pulsa un botón para leer las noticias \U0001f447")

    tg.send_message(
        token,
        chat_id,
        "\n".join(lines),
        reply_markup=_morning_keyboard(),
        disable_preview=True,
    )


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
    if text == SUMMARY_BUTTON:
        text = "/resumen"
    if not text.startswith("/"):
        tg.send_message(
            token,
            chat_id,
            "No te he entendido. Escribe /ayuda para ver los comandos.",
            reply_markup=REPLY_KEYBOARD,
            disable_preview=True,
        )
        return

    cmd = text.split()[0].lstrip("/").split("@")[0].lower()
    if cmd in ("start", "ayuda", "help"):
        tg.send_message(
            token, chat_id, HELP_TEXT, reply_markup=REPLY_KEYBOARD, disable_preview=True
        )
    elif cmd == "resumen":
        now_madrid = datetime.now(ZoneInfo(config.TIMEZONE))
        send_morning(
            state,
            token,
            chat_id,
            now_madrid,
            title="\U0001f4cb <b>Resumen de ahora</b>",
        )
    elif cmd == "todo":
        deliver_all(state, token, chat_id)
    elif cmd in config.CATEGORIES:
        deliver_category(cmd, state, token, chat_id)
    else:
        tg.send_message(
            token,
            chat_id,
            "Comando no reconocido. Escribe /ayuda.",
            reply_markup=REPLY_KEYBOARD,
            disable_preview=True,
        )


def is_summary_time(now_madrid):
    """Desde las 08:30 hasta antes de las 12:00 (hora de Madrid)."""
    start = (config.SEND_HOUR, config.SEND_MINUTE)
    return start <= (now_madrid.hour, now_madrid.minute) and (
        now_madrid.hour < config.SEND_WINDOW_END_HOUR
    )


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
        except Exception as exc:  # noqa: BLE001 — un update roto no debe tumbar el resto
            log(f"[bot] error procesando update {update.get('update_id')}: {exc}")

    # 2) Resumen de la manana (08:30 Madrid, una vez al dia)
    now_madrid = datetime.now(ZoneInfo(config.TIMEZONE))
    today = now_madrid.strftime("%Y-%m-%d")
    force = os.environ.get("FORCE_MORNING") == "1"
    in_window = is_summary_time(now_madrid)
    if force or (state.get("last_summary_date") != today and in_window):
        log(f"[bot] enviando resumen de la manana (force={force})")
        try:
            send_morning(state, token, chat_id, now_madrid)
            if not force:  # en modo test no marcamos, para no bloquear el real
                state["last_summary_date"] = today
        except Exception as exc:  # noqa: BLE001 — sin resumen, pero el estado se guarda
            log(f"[bot] error enviando el resumen: {exc}")

    state_mod.save(state)
    log(
        f"[bot] listo. updates={len(updates)} offset={state['offset']} "
        f"sent_cache={len(state['sent'])}"
    )


if __name__ == "__main__":
    main()
