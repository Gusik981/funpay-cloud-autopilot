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
if not GOLDEN_KEY and os.path.exists('config.json'):
    with open('config.json', 'r', encoding='utf-8') as f:
        GOLDEN_KEY = json.load(f).get('golden_key')

if not GOLDEN_KEY:
    print("ОШИБКА: GOLDEN_KEY не найден!")
    sys.exit(1)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'

def log(msg):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] {msg}", flush=True)

def main():
    log("=== ЗАПУСК ОБЛАЧНОГО АВТОПОДНЯТИЯ FUNPAY ===")
    session = requests.Session()
    session.cookies.set('golden_key', GOLDEN_KEY, domain='funpay.com')
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://funpay.com'
    }

    # 1. Авторизация
    try:
        r = session.get('https://funpay.com/', headers={'User-Agent': USER_AGENT}, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        user_elem = soup.select_one('.user-link-name')
        balance_elem = soup.select_one('.badge-balance')
        
        body = soup.find('body')
        user_id = None
        if body and body.has_attr('data-app-data'):
            app_data = json.loads(body['data-app-data'])
            user_id = app_data.get('userId')
            
        if not user_elem:
            log("ОШИБКА: Не удалось войти по golden_key.")
            sys.exit(1)
            
        username = user_elem.text.strip()
        balance = balance_elem.text.strip() if balance_elem else '0 ₽'
        log(f"Вход выполнен: {username} (ID: {user_id}) | Баланс: {balance}")
    except Exception as e:
        log(f"Сетевая ошибка при входе: {e}")
        sys.exit(1)

    # 2. Сбор категорий
    try:
        url = f'https://funpay.com/users/{user_id}/'
        r = session.get(url, headers={'User-Agent': USER_AGENT}, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')

        cats = []
        for h in soup.select('h3, h4'):
            a = h.find('a')
            if a and '/lots/' in a.get('href', ''):
                cat_name = a.text.strip()
                cat_href = a['href']
                node_id = cat_href.strip('/').split('/')[-1]
                cats.append({'name': cat_name, 'href': cat_href, 'node_id': node_id})
        
        log(f"Найдено {len(cats)} категорий с товарами на аккаунте.")
    except Exception as e:
        log(f"Ошибка при получении категорий: {e}")
        sys.exit(1)

    # 3. Поднятие лотов
    success_count = 0
    cooldown_count = 0

    for idx, cat in enumerate(cats, 1):
        trade_url = f"https://funpay.com/lots/{cat['node_id']}/trade"
        try:
            tr_res = session.get(trade_url, headers={'User-Agent': USER_AGENT}, timeout=15)
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
            
            h_post = headers.copy()
            h_post['Referer'] = trade_url
            if csrf_token:
                h_post['X-CSRF-Token'] = csrf_token
            
            payload = {
                'game_id': game_id,
                'node_id': node_id,
                'node_ids[]': [node_id],
                'csrf_token': csrf_token
            }
            
            res = session.post('https://funpay.com/lots/raise', data=payload, headers=h_post, timeout=15)
            
            if res.status_code == 200:
                data = res.json()
                if not data.get('error'):
                    log(f"[{idx}/{len(cats)}] ✔ УСПЕШНО ПОДНЯТО: {cat['name']}")
                    success_count += 1
                else:
                    wait_sec = data.get('wait', 0)
                    log(f"[{idx}/{len(cats)}] ⏳ {cat['name']}: {data.get('msg')} ({wait_sec // 60} мин)")
                    cooldown_count += 1
            elif res.status_code == 428:
                log(f"[{idx}/{len(cats)}] ⏳ {cat['name']}: Кулдаун активен (код 428)")
                cooldown_count += 1
            else:
                log(f"[{idx}/{len(cats)}] Статус {res.status_code} для {cat['name']}")
        except Exception as e:
            log(f"[{idx}/{len(cats)}] Ошибка {cat['name']}: {e}")
        
        time.sleep(random.uniform(1.0, 1.8))

    log(f"=== ЗАВЕРШЕНО: Успешно поднято: {success_count} | Ожидают кулдаун: {cooldown_count} ===")

if __name__ == '__main__':
    main()
