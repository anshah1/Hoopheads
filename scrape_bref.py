from bs4 import BeautifulSoup
from io import StringIO
from time import sleep
import random
import unidecode, unicodedata
import re
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

# Players missing or misspelled in data/sr_bio.json (rookies who weren't drafted yet
# at snapshot time, or name variants get_player_suffix can't resolve) — hand-verified
# bref URLs. TEAM/HEIGHT/BIRTHDAY get pulled from their own bref page, same as everyone else.
MANUAL_PLAYERS = {
    'Bub Carrington':   'https://www.basketball-reference.com/players/c/carrica01.html',
    'Jimmy Butler':     'https://www.basketball-reference.com/players/b/butleji01.html',
    'Robert Williams':  'https://www.basketball-reference.com/players/w/williro04.html',
    'Yang Hansen':      'https://www.basketball-reference.com/players/y/yangha01.html',
    'Jalen Williams':   'https://www.basketball-reference.com/players/w/willija06.html',
    'Jaylin Williams':  'https://www.basketball-reference.com/players/w/willija07.html',
    'Mark Williams':    'https://www.basketball-reference.com/players/w/willima07.html',
    "Royce O'Neale":    'https://www.basketball-reference.com/players/o/onealro01.html',
    'Clint Capela':     'https://www.basketball-reference.com/players/c/capelca01.html',
    'Ron Holland':      'https://www.basketball-reference.com/players/h/hollaro01.html',
    'TJ McConnell':     'https://www.basketball-reference.com/players/m/mccontj01.html',
    'Kam Jones':        'https://www.basketball-reference.com/players/j/joneska03.html',
    'Egor Demin':       'https://www.basketball-reference.com/players/d/demineg01.html',
    'PJ Washington':    'https://www.basketball-reference.com/players/w/washipj01.html',
    'Bronny James':     'https://www.basketball-reference.com/players/j/jamesbr02.html',
    'Maxi Kleber':      'https://www.basketball-reference.com/players/k/klebima01.html',
    'Devin Carter':     'https://www.basketball-reference.com/players/c/cartede02.html',
    'Cody Williams':    'https://www.basketball-reference.com/players/w/willico04.html',
    'Xavier Tillman':   'https://www.basketball-reference.com/players/t/tillmxa01.html',
    'Keshad Johnson':   'https://www.basketball-reference.com/players/j/johnske10.html',
    'Walter Clayton':   'https://www.basketball-reference.com/players/c/claytwa01.html',
    'GG Jackson':       'https://www.basketball-reference.com/players/j/jacksgg01.html',
    'AJ Green':         'https://www.basketball-reference.com/players/g/greenaj01.html',
}

# bref's per_game_stats "Team" column uses these abbreviations; our data uses nicknames
TEAM_ABBR_TO_NICKNAME = {
    'ATL': 'Hawks', 'BOS': 'Celtics', 'BRK': 'Nets', 'CHO': 'Hornets', 'CHI': 'Bulls',
    'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets', 'DET': 'Pistons', 'GSW': 'Warriors',
    'HOU': 'Rockets', 'IND': 'Pacers', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MEM': 'Grizzlies',
    'MIA': 'Heat', 'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks',
    'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHO': 'Suns', 'POR': 'Trail Blazers',
    'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors', 'UTA': 'Jazz', 'WAS': 'Wizards',
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

def clean_for_compare(s):
    # letters and spaces only, so "A.J. Green" and "AJ Green" compare equal
    # regardless of which side bref or the source data put the punctuation on
    return re.sub(r'[^a-z ]', '', s.lower()).strip()

GENERATIONAL_SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}

def strip_generational_suffix(name):
    # bref never shows Jr./Sr./II/III/IV in a player's page title, so a name
    # that still has one on it will never string-match the page and get
    # rejected after 5 failed attempts (e.g. "Robert Williams III")
    parts = name.split(' ')
    if len(parts) > 1 and parts[-1].rstrip('.').lower() in GENERATIONAL_SUFFIXES:
        return ' '.join(parts[:-1])
    return name

def get_player_suffix(name):
    normalized = unidecode.unidecode(unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8'))
    normalized = strip_generational_suffix(normalized)
    parts = normalized.split(' ')
    if len(parts) < 2:
        return None
    # bref ids are letters only — strip punctuation before slicing, or apostrophes
    # and periods eat slots (O'Neale -> o'nea instead of oneal, P.J. -> p. instead of pj)
    first_part = re.sub(r'[^a-z]', '', parts[0].lower())[:2]
    last_part = re.sub(r'[^a-z]', '', ''.join(parts[1:]).lower())[:5]
    if not first_part or not last_part:
        return None
    initial = last_part[0]
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
            page_name = unidecode.unidecode(h1.find('span').text)
            if clean_for_compare(page_name) == clean_for_compare(normalized):
                return suffix
            num = int(''.join(c for c in suffix if c.isdigit())) + 1
            num_str = f"0{num}" if num < 10 else str(num)
            suffix = f'/players/{initial}/{last_part}{first_part}{num_str}.html'
    return None

def fetch_stats_row(soup):
    table = soup.find('table', {'id': 'per_game_stats'})
    if not table:
        return None, "no per_game table"
    df = pd.read_html(StringIO(str(table)))[0]
    row = df[df['Season'] == '2025-26']
    if row.empty:
        return None, f"no 2025-26 row, seasons available: {df['Season'].tolist()}"
    games = int(row['G'].values[0])
    if games < 30:
        return None, f"only {games} games"
    return row, None

def parse_bio(soup):
    """Pull height and birthday straight off the player's own bref page (the 'meta' bio box)."""
    meta = soup.find('div', id='meta')
    height = ''
    birthday = ''
    if meta:
        height_match = re.search(r'(\d-\d{1,2}),\s*\d+lb', meta.get_text())
        if height_match:
            height = height_match.group(1)
        born_span = meta.find('span', id='necro-birth')
        if born_span and born_span.get('data-birth'):
            birthday = born_span['data-birth']
    return height, birthday

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
used_slugs = set(info['SLUG'] for info in stats.values() if 'SLUG' in info)
print(f"{len(already_done)} already have stats, skipping them\n")

# Pass 1: hand-verified manual players. Runs first so their curated data wins
# if a name in sr_bio.json turns out to be the same physical player.
print(f"--- Manual players ({len(MANUAL_PLAYERS)}) ---")
for i, (name, url) in enumerate(MANUAL_PLAYERS.items()):
    slug = url.replace('https://www.basketball-reference.com', '')
    if name in already_done or slug in used_slugs:
        print(f"[manual {i+1}/{len(MANUAL_PLAYERS)}] {name} — skipping")
        continue

    print(f"[manual {i+1}/{len(MANUAL_PLAYERS)}] {name}...")
    r = bref_get(url)
    if r is None or r.status_code != 200:
        print(f"  -> Status {r.status_code if r else 'None'}")
        continue

    try:
        soup = BeautifulSoup(r.content, 'html.parser')
        row, err = fetch_stats_row(soup)
        if err:
            print(f"  -> {err}")
            continue

        team_abbr = row['Team'].values[0]
        team = TEAM_ABBR_TO_NICKNAME.get(team_abbr, '')
        if not team:
            print(f"  -> WARNING: unrecognized team abbreviation {team_abbr!r}")

        height, birthday = parse_bio(soup)
        if not height or not birthday:
            print(f"  -> WARNING: couldn't parse bio (height={height!r}, birthday={birthday!r})")

        entry = {
            'TEAM': team,
            'HEIGHT': height,
            'BIRTHDAY': birthday,
            'NAME': name,
            'SLUG': slug,
            'PPG': round(float(row['PTS'].values[0]), 1),
            'RPG': round(float(row['TRB'].values[0]), 1),
            'APG': round(float(row['AST'].values[0]), 1),
        }
        stats[name] = entry
        used_slugs.add(slug)
        print(f"  -> {entry['PPG']} PPG, {entry['RPG']} RPG, {entry['APG']} APG")
        with open('data/bref_stats.json', 'w') as f:
            json.dump(stats, f, indent=4)
    except KeyboardInterrupt:
        with open('data/bref_stats.json', 'w') as f:
            json.dump(stats, f, indent=4)
        print(f"\nInterrupted during manual players [{i+1}/{len(MANUAL_PLAYERS)}] — saved")
        sys.exit(0)
    except Exception as e:
        print(f"  -> Error: {e}")
        continue

    sleep(random.uniform(6, 14))

# Pass 2: full roster from sr_bio.json
print(f"\n--- Roster from sr_bio.json ({len(bio)}) ---")
for i, (name, info) in enumerate(bio.items()):
    if name in already_done:
        print(f"[{i+1}/{len(bio)}] {name} — skipping")
        continue

    print(f"[{i+1}/{len(bio)}] {name}...")
    suffix = get_player_suffix(name)
    if not suffix:
        print(f"  -> Couldn't find bref page")
        continue
    if suffix in used_slugs:
        print(f"  -> Already have this player via a manual entry, skipping")
        continue

    r = bref_get(f'https://www.basketball-reference.com{suffix}')
    if r is None or r.status_code != 200:
        print(f"  -> Status {r.status_code if r else 'None'}")
        continue

    try:
        soup = BeautifulSoup(r.content, 'html.parser')
        row, err = fetch_stats_row(soup)
        if err:
            print(f"  -> {err}")
            continue
        entry = dict(info)
        entry['NAME'] = name
        entry['SLUG'] = suffix
        entry['PPG'] = round(float(row['PTS'].values[0]), 1)
        entry['RPG'] = round(float(row['TRB'].values[0]), 1)
        entry['APG'] = round(float(row['AST'].values[0]), 1)
        stats[name] = entry
        used_slugs.add(suffix)
        print(f"  -> {entry['PPG']} PPG, {entry['RPG']} RPG, {entry['APG']} APG")
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

def slug_id(suffix):
    return suffix.split('/')[-1].replace('.html', '')

final = {}
for p, info in stats.items():
    if 'PPG' in info and 'RPG' in info and 'APG' in info and info.get('SLUG'):
        final[slug_id(info['SLUG'])] = info

with open('players.json', 'w') as f:
    json.dump(final, f, indent=4)
print(f"\nDone — {len(final)} players saved to players.json")
