import os
import sys
import time
import json
import random
import datetime
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

GOLDEN_KEY = os.environ.get('GOLDEN_KEY')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
REPO = os.environ.get('GITHUB_REPOSITORY', 'Gusik981/funpay-cloud-autopilot')

if not GOLDEN_KEY and os.path.exists('config.json'):
    with open('config.json', 'r', encoding='utf-8') as f:
        GOLDEN_KEY = json.load(f).get('golden_key')

if not GOLDEN_KEY:
    print("ОШИБКА: GOLDEN_KEY не найден!")
    sys.exit(1)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'

# 4 часа 45 минут
MAX_RUN_SECONDS = 4 * 3600 + 45 * 60

def log(msg):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] {msg}", flush=True)

def trigger_next_worker():
    """Запуск следующего воркера через GitHub API для бесконечной эстафеты"""
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
            log(f"Статус вызова dispatch: {res.status_code} ({res.text[:100]})")
    except Exception as e:
        log(f"Ошибка передачи эстафеты: {e}")

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
        log("Авторизация на FunPay...")
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
                log("ОШИБКА: Не удалось войти по golden_key. Возможно, ключ устарел.")
                return False
                
            self.username = user_elem.text.strip()
            balance = balance_elem.text.strip() if balance_elem else '0 ₽'
            log(f"Вход выполнен: {self.username} (ID: {self.user_id}) | Баланс: {balance}")
            return True
        except Exception as e:
            log(f"Сетевая ошибка при авторизации: {e}")
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
            log(f"Актуализировано категорий с товарами: {len(self.categories)}")
            return cats
        except Exception as e:
            log(f"Ошибка загрузки категорий: {e}")
            return self.categories

    def raise_all_lots(self):
        # Перезагружаем категории раз в час (вдруг продавец добавил новый товар)
        if (time.time() - self.last_categories_reload) > 3600 or not self.categories:
            self.load_categories()

        log("--- СТАРТ ЦИКЛА ПОДНЯТИЯ ЛОТОВ ---")
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
                            log(f"[{idx}/{len(self.categories)}] ✔ УСПЕШНО ПОДНЯТО: {cat['name']}")
                            success_count += 1
                        else:
                            wait_sec = data.get('wait', 7200)
                            if wait_sec < min_wait and wait_sec > 0:
                                min_wait = wait_sec
                            log(f"[{idx}/{len(self.categories)}] ⏳ {cat['name']}: {data.get('msg')} ({wait_sec // 60} мин)")
                            cooldown_count += 1
                    except Exception:
                        log(f"[{idx}/{len(self.categories)}] Ответ без JSON: {res.text[:60]}")
                elif res.status_code == 428:
                    log(f"[{idx}/{len(self.categories)}] ⏳ {cat['name']}: Кулдаун активен (428)")
                    cooldown_count += 1
                elif res.status_code == 401:
                    log(f"[{idx}/{len(self.categories)}] Сессия истекла (401), переавторизация...")
                    self.authenticate()
                else:
                    log(f"[{idx}/{len(self.categories)}] Статус {res.status_code} для {cat['name']}")
            except Exception as e:
                log(f"[{idx}/{len(self.categories)}] Ошибка {cat['name']}: {e}")
            
            time.sleep(random.uniform(0.8, 1.4))

        next_wait = max(min_wait, 120)
        log(f"ИТОГ КРУГА: Поднято: {success_count} | Ожидают: {cooldown_count}. Следующий круг через ~{next_wait // 60} мин.")
        return next_wait

    def ping_online(self):
        try:
            self.session.get('https://funpay.com/', headers={'User-Agent': USER_AGENT}, timeout=10)
        except Exception:
            pass

    def run(self):
        log("=== БОТ ЗАПУЩЕН В БЕСКОНЕЧНОМ ОБЛАЧНОМ РЕЖИМЕ 24/7 ===")
        start_time = time.time()

        while not self.authenticate():
            log("Повтор авторизации через 30 сек...")
            time.sleep(30)

        self.load_categories()

        while True:
            # Проверка передачи эстафеты (4 часа 45 минут)
            elapsed_total = time.time() - start_time
            if elapsed_total >= MAX_RUN_SECONDS:
                log("Воркер отработал 4ч 45м. Передаем эстафету следующему воркеру...")
                trigger_next_worker()
                time.sleep(40)
                log("Завершение текущей смены (следующий воркер подхвачен).")
                break

            try:
                wait_time = self.raise_all_lots()
                
                # Цикл ожидания с пингом каждые 90 секунд (вечный Онлайн)
                elapsed = 0
                while elapsed < wait_time:
                    sleep_chunk = min(90, wait_time - elapsed)
                    time.sleep(sleep_chunk)
                    elapsed += sleep_chunk
                    self.ping_online()
                    remaining = (wait_time - elapsed) // 60
                    log(f"Статус: ОНЛАЙН 24/7 | До следующего автоподнятия лотов: ~{remaining} мин.")

                    if (time.time() - start_time) >= MAX_RUN_SECONDS:
                        break

            except Exception as e:
                log(f"Сбой в цикле: {e}. Перезапуск через 30 секунд...")
                time.sleep(30)

if __name__ == '__main__':
    bot = ImmortalFunPayBot()
    bot.run()
