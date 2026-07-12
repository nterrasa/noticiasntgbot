"""Configuracion del bot: categorias, fuentes RSS y ajustes generales.

No hay secretos aqui. El BOT_TOKEN y el CHAT_ID se leen de variables de
entorno (GitHub Secrets) en bot.py, nunca se escriben en el codigo.
"""

# ---------------------------------------------------------------------------
# Zona horaria y hora del resumen de la manana
# ---------------------------------------------------------------------------
TIMEZONE = "Europe/Madrid"     # gestiona automaticamente verano/invierno (DST)
SEND_HOUR = 9                  # enviar el resumen a partir de las 09:00 Madrid
SEND_WINDOW_END_HOUR = 12      # ...pero solo hasta las 12:00 (si Actions estuvo
                               #    caido toda la manana, se salta el dia)

# ---------------------------------------------------------------------------
# Limites de volumen ("Moderado")
# ---------------------------------------------------------------------------
MAX_PER_CATEGORY = 5           # noticias por categoria en un comando/boton
MAX_PER_CATEGORY_TODO = 3      # noticias por categoria cuando se pide /todo
MAX_PER_SOURCE = 6             # tope de items que se leen de cada fuente
MORNING_FRESH_HOURS = 30       # ventana para contar "novedades" en el resumen
MAX_AGE_DAYS = 14              # nunca mostrar nada mas viejo que esto

# ---------------------------------------------------------------------------
# Anti-duplicados
# ---------------------------------------------------------------------------
SENT_TTL_DAYS = 7              # cuanto recordamos una noticia ya enviada

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
MSG_DELAY_SECONDS = 0.6        # pausa entre mensajes para no tocar limites
HTTP_TIMEOUT = 25              # timeout de red (segundos)

# ---------------------------------------------------------------------------
# Categorias y fuentes
# type "rss"   -> feed nativo: titular + descripcion + enlace real (buen preview)
# type "gnews" -> Google News RSS (fuente sin RSS propio): titular + enlace
#                 redirigido; sin descripcion util y preview generico.
# ---------------------------------------------------------------------------
CATEGORIES = {
    "granjas": {
        "emoji": "\U0001F69C",  # tractor
        "title": "Granjas (UK & Irlanda)",
        "sources": [
            {"name": "Agriland", "type": "rss",
             "url": "https://www.agriland.ie/feed/"},
            {"name": "Farmers Weekly", "type": "gnews",
             "url": "https://news.google.com/rss/search?q=when:3d+site:fwi.co.uk&hl=en-GB&gl=GB&ceid=GB:en"},
            {"name": "Farmers Guardian", "type": "gnews",
             "url": "https://news.google.com/rss/search?q=when:3d+site:farmersguardian.com&hl=en-GB&gl=GB&ceid=GB:en"},
        ],
    },
    "agricola": {
        "emoji": "\U0001F33E",  # ears of rice
        "title": "Agrícola (España & Cataluña)",
        "sources": [
            {"name": "Agroinformación", "type": "rss",
             "url": "https://www.agroinformacion.com/feed/"},
            {"name": "Interempresas Agrícola", "type": "gnews",
             "url": "https://news.google.com/rss/search?q=when:4d+site:interempresas.net+agricola&hl=es&gl=ES&ceid=ES:es"},
            {"name": "Agricultura Catalunya", "type": "gnews",
             "url": "https://news.google.com/rss/search?q=when:4d+agricultura+Catalunya&hl=ca&gl=ES&ceid=ES:ca"},
        ],
    },
    "cine": {
        "emoji": "\U0001F3AC",  # clapper board
        "title": "Cine & Audiovisual",
        "sources": [
            {"name": "Audiovisual451", "type": "rss",
             "url": "https://www.audiovisual451.com/feed/"},
            {"name": "Panorama Audiovisual", "type": "rss",
             "url": "https://www.panoramaaudiovisual.com/feed/"},
            {"name": "Marketing Directo", "type": "gnews",
             "url": "https://news.google.com/rss/search?q=when:4d+site:marketingdirecto.com&hl=es&gl=ES&ceid=ES:es"},
            {"name": "Motionographer", "type": "rss",
             "url": "https://motionographer.com/feed/"},
            {"name": "No Film School", "type": "rss",
             "url": "https://nofilmschool.com/rss.xml"},
            {"name": "ControlPublicidad", "type": "gnews",
             "url": "https://news.google.com/rss/search?q=when:5d+site:controlpublicidad.com&hl=es&gl=ES&ceid=ES:es"},
            {"name": "Reason Why", "type": "gnews",
             "url": "https://news.google.com/rss/search?q=when:5d+site:reasonwhy.es&hl=es&gl=ES&ceid=ES:es"},
        ],
    },
    "coches": {
        "emoji": "\U0001F697",  # car
        "title": "Coches",
        "sources": [
            {"name": "Motorpasión", "type": "rss",
             "url": "https://www.motorpasion.com/rss2.xml"},
            {"name": "Diariomotor", "type": "rss",
             "url": "https://www.diariomotor.com/feed/"},
            {"name": "Car and Driver", "type": "rss",
             "url": "https://www.caranddriver.com/es/rss/all.xml/"},
        ],
    },
}

# Orden en que se muestran las categorias
CATEGORY_ORDER = ["granjas", "agricola", "cine", "coches"]

# User-Agent para pedir los feeds (algunos servidores rechazan el de por defecto)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
