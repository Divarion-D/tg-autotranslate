# tg-autotranslate

Userbot для Telegram, который переводит твои исходящие сообщения на английский.

Бот не отправляет новое сообщение, а **редактирует твоё на месте**: ты пишешь по-русски, и через секунду текст заменяется переводом. Поскольку сообщение то же самое, сохраняется всё остальное:

- ответы (reply) и треды;
- фото, видео и файлы (переводится подпись);
- редактирование: если исправишь сообщение по-русски, оно переведётся снова.

## Почему userbot, а не обычный бот

Обычный бот (Bot API) не может писать от твоего имени. Userbot работает через твой аккаунт (Telethon, клиентский API), поэтому может менять твои сообщения.

## Установка на сервер

Нужен Python 3.9+. Ниже путь `/opt/tg-autotranslate`, подставь свой.

1. Получи `api_id` и `api_hash` на https://my.telegram.org (раздел *API development tools*).
2. Склонируй проект и создай виртуальное окружение:
   ```bash
   sudo mkdir -p /opt/tg-autotranslate
   sudo chown $USER: /opt/tg-autotranslate
   git clone <url-репозитория> /opt/tg-autotranslate
   cd /opt/tg-autotranslate
   python3 -m venv venv
   venv/bin/pip install -r requirements.txt
   ```
   Если `venv` не создаётся на Debian/Ubuntu: `sudo apt install python3-venv`.
3. Сохрани ключи в `.env` (он в `.gitignore`):
   ```bash
   echo "TG_API_ID=12345" > .env
   echo "TG_API_HASH=xxxxxxxxxxxxxxxx" >> .env
   echo "translators_default_region=EN" >> .env
   chmod 600 .env
   ```
   `translators_default_region` нужен, чтобы библиотека `translators` при старте не определяла регион через `geolocation.onetrust.com`: если сервер до него не достучится, бот падает с ошибкой `Unable to find server backend`.

   Если Telegram с сервера недоступен, добавь прокси. Через него пойдёт только подключение к Telegram, переводчики работают напрямую:
   ```bash
   echo "TG_PROXY=socks5://user:pass@1.2.3.4:1080" >> .env
   ```
   Поддерживаются `socks5://`, `socks4://` и `http://`. Если логина нет, убери `user:pass@`. MTProto-прокси (ссылки `tg://proxy?...`) не поддерживаются.
4. Первый запуск сделай вручную, чтобы войти в аккаунт:
   ```bash
   set -a; . ./.env; set +a
   venv/bin/python main.py
   ```
   Telethon попросит номер телефона и код из Telegram. После входа появится `translator.session`, дальше вход не нужен. Останови бота через `Ctrl+C` и запусти в фоне одним из способов ниже.

### Запуск в фоне через systemd (рекомендуется)

Бот сам поднимется после перезагрузки сервера и перезапустится при падении.

```bash
sudo tee /etc/systemd/system/tg-autotranslate.service > /dev/null <<EOF
[Unit]
Description=Telegram translator userbot
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=/opt/tg-autotranslate
EnvironmentFile=/opt/tg-autotranslate/.env
ExecStart=/opt/tg-autotranslate/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now tg-autotranslate
```

Управление:

```bash
sudo systemctl status tg-autotranslate    # состояние
journalctl -u tg-autotranslate -f         # логи в реальном времени
sudo systemctl restart tg-autotranslate   # перезапуск (например, после git pull)
sudo systemctl stop tg-autotranslate      # остановка
```

### Запуск в фоне без systemd

Если нет root-доступа:

```bash
cd /opt/tg-autotranslate
set -a; . ./.env; set +a
nohup venv/bin/python main.py > bot.log 2>&1 &
```

Логи: `tail -f bot.log`. Остановка: `pkill -f "venv/bin/python main.py"`. После перезагрузки сервера бот придётся запустить заново.

### Обновление

```bash
cd /opt/tg-autotranslate
git pull
venv/bin/pip install -r requirements.txt
sudo systemctl restart tg-autotranslate
```

## Использование

Перевод включается отдельно для каждого чата:

| Действие | Результат |
|---|---|
| Написать `.en` в чате | Перевод включён, на секунду появится «EN on» |
| Ещё раз `.en` | Перевод выключен, появится «EN off» |

Команда `.en` сразу удаляется, собеседник её не увидит. Список чатов с включённым переводом хранится в `enabled_chats.json` и не сбрасывается при перезапуске.

Переводятся только сообщения с кириллицей. Английский текст, ссылки, стикеры и команды ботов остаются как есть.

## Переводчик

Перевод идёт через библиотеку [`translators`](https://github.com/UlionTse/translators), ключи не нужны. Переводчики пробуются по порядку: **Google → Bing → DeepL → ModernMT**. Если один не отвечает, бот берёт следующий. Порядок задаётся в `ENGINES` в `main.py`.

Если не сработал ни один, оригинал остаётся без изменений, а ошибка пишется в лог.

## Ограничения

- Собеседник может на мгновение увидеть русский оригинал в push-уведомлении, потому что текст заменяется уже после отправки.
- Форматирование (жирный текст, курсив, ссылки под словами) при переводе теряется.
- Перевод работает, только пока скрипт запущен. Чтобы он работал постоянно, запусти его на сервере (см. «Установка на сервер»).
- Telegram разрешает редактировать сообщения только в течение 48 часов, поэтому старые сообщения при правке не переведутся.

## Безопасность

`translator.session` даёт полный доступ к твоему аккаунту. Не публикуй его и не добавляй в git.

## Файлы

- `main.py`: весь код бота
- `requirements.txt`: зависимости (`telethon`, `translators`, `python-socks` для прокси Telegram)
- `enabled_chats.json`: чаты с включённым переводом (создаётся автоматически)
- `translator.session`: сессия Telegram (создаётся при первом входе)
