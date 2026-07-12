# 📰 Bot de Noticias de Telegram (gratis, con GitHub Actions)

Un bot de Telegram que **cada mañana a las 09:00 (hora de Madrid)** te manda un
resumen de novedades por sectores y que además responde a comandos cuando
quieras. **No necesita servidor**: se ejecuta gratis en GitHub Actions.

- 🌅 **Resumen de la mañana**: un mensaje de "buenos días" con un teaser por
  sector y **botones** para leer las noticias de cada categoría.
- 💬 **Comandos** en cualquier momento: `/granjas`, `/agricola`, `/cine`,
  `/coches`, `/todo`, `/ayuda`.
- 🆓 **Modo gratis**: cada noticia es titular + 1-2 frases (la descripción del
  RSS) + enlace, con la vista previa de Telegram. Sin traducción (las noticias
  de UK/Irlanda salen en inglés).

---

## 📂 Qué es cada archivo

| Archivo | Para qué sirve |
|---|---|
| `bot.py` | Programa principal (lee comandos + decide si toca el resumen). |
| `config.py` | **Categorías, fuentes RSS y ajustes** (aquí tocas si quieres cambiar fuentes/horas). |
| `news.py` | Descarga y limpieza de las noticias. |
| `tg.py` | Llamadas a la API de Telegram. |
| `state.py` | Lee/guarda `state.json`. |
| `state.json` | Memoria del bot (último mensaje leído, fecha del último resumen, noticias ya enviadas). Se actualiza solo. |
| `.github/workflows/bot.yml` | El "reloj": ejecuta el bot cada 5 minutos. |
| `requirements.txt` | Dependencias de Python. |

---

## ✅ Reparto: qué hago yo (ya hecho) y qué haces tú

**Ya está hecho (el código):** todo `bot.py`, la lógica de comandos, el resumen
con botones, el anti-duplicados, el workflow y las fuentes RSS verificadas.

**Lo tienes que hacer tú una sola vez (10 min):** crear el bot en BotFather,
sacar tu `chat_id`, subir esto a un repo **público** de GitHub y meter dos
Secrets (`BOT_TOKEN` y `CHAT_ID`). Es lo que viene ahora.

---

## 🛠️ Puesta en marcha (paso a paso)

### Paso 1 — Crear el bot y obtener el `BOT_TOKEN`
1. En Telegram abre **@BotFather**.
2. Envía `/newbot` y sigue las instrucciones (nombre y un usuario que acabe en
   `bot`, p. ej. `mis_noticias_bot`).
3. BotFather te da un **token** con esta pinta:
   `123456789:AAE...xyz`. **Guárdalo**, es tu `BOT_TOKEN`.
4. Abre el chat con **tu** bot y pulsa **Start** (o escribe `/start`). Esto es
   necesario para que el bot pueda escribirte.

### Paso 2 — Obtener tu `CHAT_ID`
La forma más fácil:
1. En Telegram abre **@userinfobot** y pulsa Start.
2. Te responde con tu **Id** (un número, p. ej. `987654321`). Ese es tu `CHAT_ID`.

> Alternativa: escribe algo a tu bot y abre en el navegador
> `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`. Busca
> `"chat":{"id":987654321,...}` → ese número es tu `CHAT_ID`.

### Paso 3 — Crear el repositorio **público** y subir el código
1. En GitHub crea un repositorio **nuevo y PÚBLICO** (importante: público = minutos
   de Actions gratis e ilimitados).
2. Sube estos archivos. Desde esta carpeta, en una terminal:
   ```bash
   git init
   git add .
   git commit -m "Bot de noticias de Telegram"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
   git push -u origin main
   ```

### Paso 4 — Configurar los Secrets
En tu repo de GitHub: **Settings → Secrets and variables → Actions → New
repository secret**. Crea **exactamente estos dos** (los nombres importan):

| Name | Secret (valor) |
|---|---|
| `BOT_TOKEN` | el token de BotFather del Paso 1 |
| `CHAT_ID` | tu id del Paso 2 |

> ⚠️ Nunca escribas el token ni el chat_id en el código. El bot los lee de estos
> Secrets. Si el token se filtra, regénalo en BotFather con `/revoke`.

### Paso 5 — Activar Actions
1. Ve a la pestaña **Actions** del repo. Si te pide habilitar los workflows,
   pulsa **"I understand my workflows, go ahead and enable them"**.
2. El bot ya se ejecutará solo cada 5 minutos.

---

## 🧪 Cómo probarlo

**Prueba rápida (recomendada), sin esperar:**
1. Pestaña **Actions** → workflow **"Bot de Noticias"** → botón **"Run
   workflow"** (menú *Run workflow* → *Run workflow*).
2. En unos segundos el bot procesa lo pendiente. Ahora, en Telegram:
   - Escríbele `/ayuda` → vuelve a **Run workflow** → deberías recibir el menú.
   - Escríbele `/coches` → **Run workflow** → deberías recibir varias noticias
     de coches con vista previa.

> Recuerda: como es gratis y se ejecuta cada 5 min, cada comando/botón tarda
> **hasta ~5 minutos** en responder (o al instante si tú lanzas "Run workflow").

**Probar el resumen de la mañana sin esperar a las 9:** la forma más sencilla es
probarlo en tu ordenador (ver abajo) con `FORCE_MORNING=1`.

**Prueba en tu ordenador (opcional):**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="123456789:AAE...xyz"
export CHAT_ID="987654321"
export FORCE_MORNING=1      # fuerza el envío del resumen de la mañana ahora
python bot.py
```
Esto responde a tus comandos pendientes y te envía el resumen de "buenos días"
con botones. (Sin `FORCE_MORNING`, el resumen solo sale entre las 09:00 y las
12:00 de Madrid.)

---

## ⚙️ Personalizar (todo en `config.py`)

- **Hora del resumen**: `SEND_HOUR = 9` (hora de Madrid).
- **Cuántas noticias**: `MAX_PER_CATEGORY` (comandos), `MAX_PER_CATEGORY_TODO`
  (`/todo`).
- **Cada cuánto revisa**: en `.github/workflows/bot.yml`, el `cron: "*/5 * * * *"`.
- **Fuentes**: edita la lista `CATEGORIES`. Cada fuente es:
  - `"type": "rss"` → un feed RSS normal (mejor vista previa).
  - `"type": "gnews"` → una búsqueda de Google News (para webs sin RSS; el enlace
    es un redirect de Google y la vista previa es más genérica).

---

## ℹ️ Notas y límites del modo gratis

- **Retraso de hasta ~5 min** en comandos y botones (es el precio de no tener
  servidor). Cero retraso solo sería posible con webhooks + servidor 24/7 (ya no
  gratis).
- **La hora exacta** del cron de GitHub Actions puede variar unos minutos según
  la carga de GitHub; por eso el resumen se manda en la **primera** ejecución a
  partir de las 09:00 (y como muy tarde a las 12:00).
- **Fuentes sin RSS propio** (Farmers Weekly, Farmers Guardian, Interempresas,
  ControlPublicidad, Reason Why, Marketing Directo) se leen vía **Google News**:
  llega el titular y el enlace, pero sin descripción y con vista previa genérica.
- **Idioma**: no se traduce; las noticias de UK/Irlanda salen en inglés.
- **Inactividad (60 días)**: GitHub puede pausar los workflows programados si el
  repo no tiene actividad. El bot hace *commit* de `state.json` en cada cambio,
  lo que ayuda a mantenerlo activo. Si aun así algún día recibes un email de
  GitHub diciendo que se ha desactivado, entra en **Actions** y pulsa **"Enable
  workflow"** (un clic) — o haz cualquier commit.

---

## 🔒 Seguridad

- El bot **solo atiende a tu `CHAT_ID`**: si otra persona encuentra el bot y le
  escribe, lo ignora.
- Secretos fuera del código: `BOT_TOKEN` y `CHAT_ID` viven en GitHub Secrets.
