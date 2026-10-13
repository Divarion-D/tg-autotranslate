"""
Userbot: переводит мои исходящие сообщения на английский, редактируя их на месте
(reply, медиа, треды сохраняются — это то же сообщение).

  pip install -r requirements.txt
  export TG_API_ID=12345 TG_API_HASH=xxxxxxxx   # https://my.telegram.org
  python main.py

В нужном чате напиши .en — перевод включится для этого чата, ещё раз — выключится.
"""
import asyncio
import json
import logging
import os
import re
from pathlib import Path

import translators as ts
from telethon import TelegramClient, events

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("translator")

STATE = Path(__file__).with_name("enabled_chats.json")
CYRILLIC = re.compile(r"[а-яё]", re.I)

enabled = set(json.loads(STATE.read_text())) if STATE.exists() else set()
ENGINES = ["google", "bing", "deepl", "modernMt"]  # по порядку, следующий — если предыдущий упал


def translate(text):
    for engine in ENGINES:
        try:
            return ts.translate_text(text, translator=engine, from_language="auto", to_language="en", timeout=10)
        except Exception as e:
            log.warning("%s: %r, пробую следующий", engine, e)
    raise RuntimeError("все переводчики недоступны")


client = TelegramClient(
    str(Path(__file__).with_name("translator")),
    int(os.environ["TG_API_ID"]),
    os.environ["TG_API_HASH"],
)


async def notify(event, text):
    note = await event.respond(text)
    await asyncio.sleep(2)
    await note.delete()


@client.on(events.NewMessage(outgoing=True))
@client.on(events.MessageEdited(outgoing=True))
async def handler(event):
    text = event.raw_text or ""

    if text.strip() == ".en":
        enabled.symmetric_difference_update({event.chat_id})
        STATE.write_text(json.dumps(sorted(enabled)))
        await event.delete()
        await notify(event, "EN on" if event.chat_id in enabled else "EN off")
        return

    # кириллица = ещё не переведено; после нашего edit текст английский, цикла нет
    if event.chat_id not in enabled or not CYRILLIC.search(text):
        return

    try:
        en = await asyncio.to_thread(translate, text)
        if en and en != text:
            await event.edit(en)
    except Exception:
        log.exception("перевод не удался, оставляю оригинал (chat %s)", event.chat_id)


client.start()
log.info("запущен, перевод включён в чатах: %s", sorted(enabled) or "нигде")
client.run_until_disconnected()
