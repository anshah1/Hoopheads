from bs4 import BeautifulSoup
from time import sleep
import random
import unidecode, unicodedata
import pandas as pd
import requests
import socks, socket
import json
import sys
from stem import Signal
from stem.control import Controller

# Route all requests through Tor
socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 9050)
socket.socket = socks.socksocket

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.basketball-reference.com/',
}

def rotate_ip():
    import socket as _socket
    real_socket = _socket.socket
    _socket.socket = _socket.socket  # temporarily use real socket
    socks.set_default_proxy()  # clear proxy
    with Controller.from_port(address='127.0.0.1', port=9051) as c:
        c.authenticate()
        c.signal(Signal.NEWNYM)
        sleep(3)
    socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 9050)  # restore proxy
    print("  Rotated Tor IP")

def bref_get(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code in (429, 403):
                print(f"  Blocked ({r.status_code}), rotating IP and retrying...")
                rotate_ip()
                continue
            return r
        except Exception as e:
            print(f"  Connection error ({e.__class__.__name__}), rotating IP and retrying...")
            rotate_ip()
    return None

def get_player_suffix(name):
    normalized = unidecode.unidecode(unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8'))
    parts = normalized.split(' ')
    if len(parts) < 2:
        return None
    initial = parts[1][0].lower()
    first_part = unidecode.unidecode(parts[0][:2].lower())
    last_part = ''.join(parts[1:])[:5].lower()
    suffix = f'/players/{initial}/{last_part}{first_part}01.html'

    for attempt in range(5):
        r = bref_get(f'https://www.basketball-reference.com{suffix}')
        if r is None or r.status_code == 404:
            return None
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            h1 = soup.find('h1')
            if not h1:
                return None
            page_name = unidecode.unidecode(h1.find('span').text).lower()
            if page_name == normalized.lower():
                return suffix
            num = int(''.join(c for c in suffix if c.isdigit())) + 1
            num_str = f"0{num}" if num < 10 else str(num)
            suffix = f'/players/{initial}/{last_part}{first_part}{num_str}.html'
    return None

# Load bio from sr_bio.json (strip the Sportradar ID)
sr_bio = json.load(open('data/sr_bio.json'))
bio = {name: {k: v for k, v in info.items() if k != 'ID'} for name, info in sr_bio.items()}
print(f"Loaded {len(bio)} players from data/sr_bio.json")

# Load existing stats so we can resume
try:
    stats = json.load(open('data/bref_stats.json'))
except FileNotFoundError:
    stats = {}

already_done = set(p for p, info in stats.items() if 'PPG' in info)
print(f"{len(already_done)} already have stats, skipping them\n")

for i, (name, info) in enumerate(bio.items()):
    if name in already_done:
        print(f"[{i+1}/{len(bio)}] {name} — skipping")
        continue

    print(f"[{i+1}/{len(bio)}] {name}...")
    suffix = get_player_suffix(name)
    if not suffix:
        print(f"  -> Couldn't find bref page")
        continue

    r = bref_get(f'https://www.basketball-reference.com{suffix}')
    if r is None or r.status_code != 200:
        print(f"  -> Status {r.status_code if r else 'None'}")
        continue

    try:
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find('table', {'id': 'per_game_stats'})
        if not table:
            print(f"  -> No per_game table")
            continue
        from io import StringIO
        df = pd.read_html(StringIO(str(table)))[0]
        row = df[df['Season'] == '2025-26']
        if row.empty:
            print(f"  -> No 2025-26 row, seasons available: {df['Season'].tolist()}")
            continue
        if row.empty:
            print(f"  -> No 2024-25 data")
            continue
        games = int(row['G'].values[0])
        if games < 30:
            print(f"  -> Only {games} games, skipping")
            continue
        entry = dict(info)
        entry['PPG'] = round(float(row['PTS'].values[0]), 1)
        entry['RPG'] = round(float(row['TRB'].values[0]), 1)
        entry['APG'] = round(float(row['AST'].values[0]), 1)
        stats[name] = entry
        print(f"  -> {entry['PPG']} PPG, {entry['RPG']} RPG, {entry['APG']} APG ({games} games)")
        with open('data/bref_stats.json', 'w') as f:
            json.dump(stats, f, indent=4)
    except KeyboardInterrupt:
        with open('data/bref_stats.json', 'w') as f:
            json.dump(stats, f, indent=4)
        print(f"\nInterrupted at [{i+1}/{len(bio)}] — saved")
        sys.exit(0)
    except Exception as e:
        print(f"  -> Error: {e}")
        continue

    sleep(random.uniform(6, 14))

final = {p: info for p, info in stats.items() if 'PPG' in info and 'RPG' in info and 'APG' in info}
with open('players.json', 'w') as f:
    json.dump(final, f, indent=4)
print(f"\nDone — {len(final)} players saved to players.json")
