"""Self-check of the bot logic, no network or Telegram: `python test_bot.py` (validate.sh runs it)."""

from datetime import UTC, datetime, timedelta

import bot
import news
import state as state_mod
import tg

sent: list[str] = []
tg.send_message = lambda token, chat_id, text, **kw: sent.append(text)
tg.answer_callback = lambda *a, **kw: None
now = datetime.now(UTC)


def item(item_id, title, hours_ago):
    return news.Item(
        item_id,
        title,
        f"https://x/{item_id}",
        "",
        "src",
        "rss",
        now - timedelta(hours=hours_ago),
    )


news.fetch_source = lambda source: [
    item("old", "Old", 24 * 30),
    item("dup", "Same title", 2),
    item("keep", "same  TITLE", 1),
    item("sent", "Already sent", 3),
    item("fresh", "Fresh", 0.5),
]

# Only the owner's chat gets answers (messages and buttons).
st = {"offset": 0, "last_summary_date": "", "sent": {}}
bot.handle_update({"message": {"chat": {"id": 7}, "text": "/ayuda"}}, st, "t", "42")
bot.handle_update(
    {"callback_query": {"id": "c", "from": {"id": 7}, "data": "cat:todo"}},
    st,
    "t",
    "42",
)
assert sent == [], sent
bot.handle_update({"message": {"chat": {"id": 42}, "text": "/ayuda"}}, st, "t", "42")
assert sent == [bot.HELP_TEXT], sent

# The fixed "Resumen" button sends the summary of right now.
sent.clear()
bot.handle_update(
    {"message": {"chat": {"id": 42}, "text": bot.SUMMARY_BUTTON}}, st, "t", "42"
)
assert len(sent) == 1 and "Resumen de ahora" in sent[0], sent

# Morning summary from 08:30 until before 12:00 (Madrid).
assert [
    bot.is_summary_time(datetime(2026, 1, 1, h, m))
    for h, m in [(8, 29), (8, 30), (9, 5), (12, 0)]
] == [False, True, True, False]

# Newest first, no repeats across sources or titles, nothing already sent or too old.
assert [i.id for i in news.get_category_items("coches", 5, {"sent"})] == [
    "fresh",
    "keep",
]
assert [
    i.id for i in news.get_category_items("coches", 5, set(), fresh_hours=0.75)
] == ["fresh"]

# Feed text can't inject HTML into the Telegram message.
assert "&lt;b&gt;x&lt;/b&gt; &amp; y" in news.format_item(item("h", "<b>x</b> & y", 0))

# Old and broken entries leave the anti-duplicate memory.
aged: dict = {
    "sent": {
        "new": now.isoformat(),
        "old": (now - timedelta(days=30)).isoformat(),
        "bad": "nope",
    }
}
state_mod.prune_sent(aged)
assert list(aged["sent"]) == ["new"], aged

print("ok")
