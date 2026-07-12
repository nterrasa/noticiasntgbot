"""Cliente minimo de la API de Telegram (solo con requests, sin librerias extra)."""

import json
import sys
import time

import requests

import config

API_BASE = "https://api.telegram.org/bot{token}/{method}"


def _call(token, method, params=None, files=None, retries=2):
    """Llama a un metodo de la API. Gestiona el limite 429 (retry_after)."""
    url = API_BASE.format(token=token, method=method)
    # Telegram acepta objetos anidados (reply_markup) como JSON string
    if params:
        params = {
            k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
            for k, v in params.items()
            if v is not None
        }
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, data=params, timeout=config.HTTP_TIMEOUT)
        except requests.RequestException as exc:
            # nunca dejar el token en el log (aunque GitHub tambien lo censura)
            safe = str(exc).replace(token, "***")
            log(f"[tg] error de red en {method}: {safe}")
            time.sleep(1)
            continue
        if resp.status_code == 429:
            retry_after = resp.json().get("parameters", {}).get("retry_after", 2)
            log(f"[tg] 429 en {method}, esperando {retry_after}s")
            time.sleep(retry_after + 1)
            continue
        data = resp.json()
        if not data.get("ok"):
            log(f"[tg] API devolvio error en {method}: {data.get('description')}")
            return None
        return data.get("result")
    return None


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def get_updates(token, offset):
    """Lee mensajes/callbacks nuevos (polling corto, sin long polling)."""
    return _call(
        token,
        "getUpdates",
        {
            "offset": offset,
            "timeout": 0,
            "allowed_updates": ["message", "callback_query"],
        },
    ) or []


def send_message(token, chat_id, text, reply_markup=None, disable_preview=False):
    """Envia un mensaje en HTML. Devuelve el mensaje enviado o None."""
    result = _call(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview,
            "reply_markup": reply_markup,
        },
    )
    # pequena pausa para no saturar el limite por chat
    time.sleep(config.MSG_DELAY_SECONDS)
    return result


def answer_callback(token, callback_id, text=None):
    """Cierra el 'cargando' de un boton. Puede fallar si el callback caduco: se ignora."""
    _call(token, "answerCallbackQuery", {"callback_query_id": callback_id, "text": text})
