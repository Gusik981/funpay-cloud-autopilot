import os
import sys
import time
import json
import random
import datetime
import asyncio
import requests
from bs4 import BeautifulSoup
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import (
    FloodWaitError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    UserAlreadyParticipantError,
    ChannelPrivateError
)

sys.stdout.reconfigure(encoding='utf-8')

GOLDEN_KEY = os.environ.get('GOLDEN_KEY')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
TG_SESSION = os.environ.get('TG_SESSION')
REPO = os.environ.get('GITHUB_REPOSITORY', 'Gusik981/funpay-cloud-autopilot')

TG_API_ID = 2040
TG_API_HASH = 'b18441a1ff607e10a989891a5462e627'

if not GOLDEN_KEY and os.path.exists('config.json'):
    with open('config.json', 'r', encoding='utf-8') as f:
        GOLDEN_KEY = json.load(f).get('golden_key')

if not GOLDEN_KEY:
    print("ОШИБКА: GOLDEN_KEY не найден!")
    sys.exit(1)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
MAX_RUN_SECONDS = 4 * 3600 + 45 * 60

def log(msg):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] {msg}", flush=True)

def trigger_next_worker():
    if not GITHUB_TOKEN:
        log("GITHUB_TOKEN отсутствует, полагаемся на cron.")
        return
    log("Передаем эстафету: запуск следующего облачного воркера...")
    try:
        url = f"https://api.github.com/repos/{REPO}/actions/workflows/auto_raise.yml/dispatches"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Immortal-Runner'
        }
        res = requests.post(url, headers=headers, json={'ref': 'main'}, timeout=15)
        if res.status_code == 204:
            log("✔ Следующий облачный воркер успешно запущен в эстафете 24/7!")
        else:
            log(f"Статус вызова dispatch: {res.status_code}")
    except Exception as e:
        log(f"Ошибка передачи эстафеты: {e}")

# ==============================================================
#                      TELEGRAM AUTO-POSTER
# ==============================================================
async def tg_poster_loop():
    if not TG_SESSION:
        log("[TG] Секрет TG_SESSION не задан.")
        return

    log("[TG] Запуск модуля автопостинга рекламы в Telegram...")
    try:
        client = TelegramClient(StringSession(TG_SESSION), TG_API_ID, TG_API_HASH)
        await client.connect()
        me = await client.get_me()
        log(f"[TG] Успешная авторизация! Аккаунт: {me.first_name} (@{me.username or 'no_user'}, ID: {me.id})")
    except Exception as e:
        log(f"[TG] Ошибка авторизации в Telegram: {e}")
        return

    messages = [
        "⚡ Хочешь, чтобы твой сервер Minecraft выглядел на миллион?\n\n🔥 В наличии готовый мега-пак **DeluxeMenus ULTRA GUI (12 в 1)**:\n• Красивые HEX/RGB градиенты и звуки кликов\n• Настроенные /menu, /donate, /profile, /buyer, /warps, /kits, /rewards\n• Установка за 2 минуты (/dm reload)\n\n🛡 Безопасная покупка с автовыдачей 24/7:\n👉 https://funpay.com/users/21235840/",
        "👑 Прокачай свой Minecraft проект топовыми меню!\n\n💎 Пак **DeluxeMenus 12 в 1** в стиле ReallyWorld & FunTime:\n✔️ /profile с выводом баланса, пинга и часов\n✔️ /donate на 5 привилегий с описанием\n✔️ /buyer (скупщик руды, мобов и фермы)\n✔️ /warps, /kits, /cases, /pass, /rules\n\n⚡ Мгновенная выдача сразу после оплаты:\n👉 https://funpay.com/users/21235840/",
        "🚀 Сборки серверов и готовые конфиги Minecraft!\n\nВ магазине на FunPay доступно:\n• Пак интерфейсов DeluxeMenus (12 меню под ключ)\n• Сборка BoxPvP 1.16-1.20+ (15 шахт, боссы)\n• Сборка Анархии (мистики, сферы, талисманы)\n• 90+ игровых конфигов и оптимизаций от 1 рубля!\n\nЗабирай с автовыдачей 24/7:\n👉 https://funpay.com/users/21235840/"
    ]
    if os.path.exists('messages.json'):
        try:
            with open('messages.json', 'r', encoding='utf-8') as f:
                messages = json.load(f)
        except Exception:
            pass

    chats = [
        '@piar_chat_vzaimno',
        '@reklama_piar_chat',
        '@minecraft_chat_ru',
        '@servers_minecraft_piar',
        '@baraholka_minecraft',
        '@piar_besplatno_chat',
        '@chat_vzaimnogo_piara'
    ]
    if os.path.exists('chats.txt'):
        try:
            with open('chats.txt', 'r', encoding='utf-8') as f:
                loaded = [l.strip() for l in f if l.strip() and not l.startswith('#')]
                if loaded:
                    chats = loaded
        except Exception:
            pass

    log(f"[TG] Загружено целевых чатов: {len(chats)}")

    while True:
        log("[TG] --- СТАРТ РАУНДА РАССЫЛКИ В ЧАТЫ ---")
        sent = 0
        for idx, chat in enumerate(chats, 1):
            text = random.choice(messages)
            try:
                # 1. Получаем сущность чата
                entity = await client.get_entity(chat)
                
                # 2. Вступаем в чат, если еще не вступили
                try:
                    await client(JoinChannelRequest(entity))
                except (UserAlreadyParticipantError, ChannelPrivateError):
                    pass
                except Exception as e:
                    log(f"[TG] Инфо вступления в {chat}: {e}")

                # 3. Отправляем сообщение
                await client.send_message(entity, text)
                sent += 1
                log(f"[TG] [{idx}/{len(chats)}] ✔ Реклама успешно отправлена в {chat}")
            except FloodWaitError as e:
                log(f"[TG] ⏳ FloodWait от Telegram: пауза {e.seconds} сек...")
                await asyncio.sleep(e.seconds + 5)
            except UserBannedInChannelError:
                log(f"[TG] [{idx}/{len(chats)}] ✖ Аккаунт ограничен (мутом/спамблоком) в чате {chat}.")
            except ChatWriteForbiddenError:
                log(f"[TG] [{idx}/{len(chats)}] ✖ В чате {chat} запрещены сообщения участников.")
            except Exception as e:
                log(f"[TG] [{idx}/{len(chats)}] Ошибка в {chat}: {type(e).__name__} ({e})")

            await asyncio.sleep(random.uniform(25, 45))

        log(f"[TG] Раунд завершен. Успешно отправлено: {sent}. Пауза 45 мин...")
        await asyncio.sleep(45 * 60)

# ==============================================================
#                      FUNPAY AUTO-RAISE BOT
# ==============================================================
class ImmortalFunPayBot:
    def __init__(self):
        self.session = requests.Session()
        self.session.cookies.set('golden_key', GOLDEN_KEY, domain='funpay.com')
        self.headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://funpay.com'
        }
        self.user_id = None
        self.username = None
        self.categories = []
        self.last_categories_reload = 0

    def authenticate(self):
        log("[FunPay] Авторизация на FunPay...")
        try:
            r = self.session.get('https://funpay.com/', headers={'User-Agent': USER_AGENT}, timeout=20)
            soup = BeautifulSoup(r.text, 'html.parser')
            user_elem = soup.select_one('.user-link-name')
            balance_elem = soup.select_one('.badge-balance')
            
            body = soup.find('body')
            if body and body.has_attr('data-app-data'):
                app_data = json.loads(body['data-app-data'])
                self.user_id = app_data.get('userId')
                
            if not user_elem:
                log("[FunPay] ОШИБКА: Не удалось войти по golden_key.")
                return False
                
            self.username = user_elem.text.strip()
            balance = balance_elem.text.strip() if balance_elem else '0 ₽'
            log(f"[FunPay] Вход выполнен: {self.username} (ID: {self.user_id}) | Баланс: {balance}")
            return True
        except Exception as e:
            log(f"[FunPay] Сетевая ошибка при авторизации: {e}")
            return False

    def load_categories(self):
        if not self.user_id:
            return []
        try:
            url = f'https://funpay.com/users/{self.user_id}/'
            r = self.session.get(url, headers={'User-Agent': USER_AGENT}, timeout=20)
            soup = BeautifulSoup(r.text, 'html.parser')

            cats = []
            for h in soup.select('h3, h4'):
                a = h.find('a')
                if a and '/lots/' in a.get('href', ''):
                    cat_name = a.text.strip()
                    cat_href = a['href']
                    node_id = cat_href.strip('/').split('/')[-1]
                    cats.append({'name': cat_name, 'href': cat_href, 'node_id': node_id})
            
            self.categories = cats
            self.last_categories_reload = time.time()
            log(f"[FunPay] Категорий на аккаунте: {len(self.categories)}")
            return cats
        except Exception as e:
            log(f"[FunPay] Ошибка загрузки категорий: {e}")
            return self.categories

    def raise_all_lots(self):
        if (time.time() - self.last_categories_reload) > 3600 or not self.categories:
            self.load_categories()

        log("[FunPay] --- СТАРТ ЦИКЛА ПОДНЯТИЯ ЛОТОВ ---")
        min_wait = 3600
        success_count = 0
        cooldown_count = 0

        for idx, cat in enumerate(self.categories, 1):
            trade_url = f"https://funpay.com/lots/{cat['node_id']}/trade"
            try:
                tr_res = self.session.get(trade_url, headers={'User-Agent': USER_AGENT}, timeout=15)
                tsoup = BeautifulSoup(tr_res.text, 'html.parser')
                
                body = tsoup.find('body')
                csrf_token = ''
                if body and body.has_attr('data-app-data'):
                    csrf_token = json.loads(body['data-app-data']).get('csrf-token', '')
                
                btn = tsoup.select_one('.js-lot-raise')
                if not btn:
                    continue
                
                game_id = btn.get('data-game')
                node_id = btn.get('data-node')
                
                h_post = self.headers.copy()
                h_post['Referer'] = trade_url
                if csrf_token:
                    h_post['X-CSRF-Token'] = csrf_token
                
                payload = {
                    'game_id': game_id,
                    'node_id': node_id,
                    'node_ids[]': [node_id],
                    'csrf_token': csrf_token
                }
                
                res = self.session.post('https://funpay.com/lots/raise', data=payload, headers=h_post, timeout=15)
                
                if res.status_code == 200:
                    try:
                        data = res.json()
                        if not data.get('error'):
                            log(f"[FunPay] [{idx}/{len(self.categories)}] ✔ ПОДНЯТО: {cat['name']}")
                            success_count += 1
                        else:
                            wait_sec = data.get('wait', 7200)
                            if wait_sec < min_wait and wait_sec > 0:
                                min_wait = wait_sec
                            log(f"[FunPay] [{idx}/{len(self.categories)}] ⏳ {cat['name']}: {data.get('msg')} ({wait_sec // 60} мин)")
                            cooldown_count += 1
                    except Exception:
                        pass
                elif res.status_code == 428:
                    log(f"[FunPay] [{idx}/{len(self.categories)}] ⏳ {cat['name']}: Кулдаун активен (428)")
                    cooldown_count += 1
                elif res.status_code == 401:
                    log(f"[FunPay] Сессия 401, переавторизация...")
                    self.authenticate()
            except Exception as e:
                log(f"[FunPay] Ошибка {cat['name']}: {e}")
            
            time.sleep(random.uniform(0.7, 1.3))

        next_wait = max(min_wait, 120)
        log(f"[FunPay] ИТОГ: Поднято: {success_count} | Ожидают: {cooldown_count}. След. круг через ~{next_wait // 60} мин.")
        return next_wait

    def ping_online(self):
        try:
            self.session.get('https://funpay.com/', headers={'User-Agent': USER_AGENT}, timeout=10)
        except Exception:
            pass

    async def run_loop(self):
        start_time = time.time()
        while not self.authenticate():
            await asyncio.sleep(30)

        self.load_categories()

        while True:
            elapsed_total = time.time() - start_time
            if elapsed_total >= MAX_RUN_SECONDS:
                log("Воркер отработал 4ч 45м. Передаем эстафету следующему воркеру...")
                trigger_next_worker()
                await asyncio.sleep(40)
                log("Завершение текущей смены (следующий воркер подхвачен).")
                break

            try:
                wait_time = await asyncio.to_thread(self.raise_all_lots)
                
                elapsed = 0
                while elapsed < wait_time:
                    sleep_chunk = min(90, wait_time - elapsed)
                    await asyncio.sleep(sleep_chunk)
                    elapsed += sleep_chunk
                    await asyncio.to_thread(self.ping_online)
                    remaining = (wait_time - elapsed) // 60
                    log(f"[FunPay] Статус: ОНЛАЙН 24/7 | До автоподнятия лотов: ~{remaining} мин.")

                    if (time.time() - start_time) >= MAX_RUN_SECONDS:
                        break
            except Exception as e:
                log(f"[FunPay] Сбой: {e}. Перезапуск через 30 сек...")
                await asyncio.sleep(30)

async def main():
    log("=== ЗАПУСК ОБЛАЧНОГО КОМПЛЕКСА 24/7: FUNPAY AUTO-RAISE + TELEGRAM AUTO-POSTER ===")
    funpay_bot = ImmortalFunPayBot()
    
    await asyncio.gather(
        funpay_bot.run_loop(),
        tg_poster_loop()
    )

if __name__ == '__main__':
    asyncio.run(main())
