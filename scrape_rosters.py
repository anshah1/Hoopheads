from bs4 import BeautifulSoup
from io import StringIO
from time import sleep
import random
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

SEASON = '2025-26'
SEASON_YEAR = 2026  # bref team roster pages are keyed by the year the season ENDS in

# NOTE for the next full rebuild (planned for early November, once nightly_scraper.py
# takes over from there): 30 assumes a season that's mostly played out. Re-running this
# early in a new season means teams won't have played 30 games yet — lower this to
# whatever's reasonable for how many games have actually been played at that point.
MIN_GAMES = 30

TEAM_ABBR_TO_NICKNAME = {
    'ATL': 'Hawks', 'BOS': 'Celtics', 'BRK': 'Nets', 'CHO': 'Hornets', 'CHI': 'Bulls',
    'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets', 'DET': 'Pistons', 'GSW': 'Warriors',
    'HOU': 'Rockets', 'IND': 'Pacers', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MEM': 'Grizzlies',
    'MIA': 'Heat', 'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks',
    'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHO': 'Suns', 'POR': 'Trail Blazers',
    'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors', 'UTA': 'Jazz', 'WAS': 'Wizards',
}

def rotate_ip():
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

def get_roster(team_abbr):
    """Returns [(name, slug), ...] for everyone on this team's end-of-season roster."""
    url = f'https://www.basketball-reference.com/teams/{team_abbr}/{SEASON_YEAR}.html'
    r = bref_get(url)
    if r is None or r.status_code != 200:
        print(f"  -> Status {r.status_code if r else 'None'} fetching roster")
        return []

    soup = BeautifulSoup(r.content, 'html.parser')
    table = soup.find('table', id='roster')
    if not table:
        print(f"  -> No roster table found")
        return []

    roster = []
    for row in table.find('tbody').find_all('tr'):
        cell = row.find('td', {'data-stat': 'player'})
        if not cell:
            continue
        link = cell.find('a')
        if not link or not link.get('href'):
            continue
        roster.append((link.text.strip(), link['href']))
    return roster

def fetch_stats_row(soup):
    table = soup.find('table', {'id': 'per_game_stats'})
    if not table:
        return None, "no per_game table"
    df = pd.read_html(StringIO(str(table)))[0]
    row = df[df['Season'] == SEASON]
    if row.empty:
        return None, f"no {SEASON} row, seasons available: {df['Season'].tolist()}"
    games = int(row['G'].values[0])
    if games < MIN_GAMES:
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

# Load existing stats so we can resume
try:
    stats = json.load(open('data/roster_stats.json'))
except FileNotFoundError:
    stats = {}

already_done = set(slug for slug, info in stats.items() if 'PPG' in info)
print(f"{len(already_done)} already have stats, skipping them\n")

for team_abbr, team_name in TEAM_ABBR_TO_NICKNAME.items():
    print(f"--- {team_name} ({team_abbr}) ---")
    roster = get_roster(team_abbr)
    print(f"  {len(roster)} players on roster")
    sleep(random.uniform(3, 6))

    for name, slug in roster:
        if slug in already_done:
            print(f"  {name} — skipping")
            continue

        print(f"  {name}...")
        r = bref_get(f'https://www.basketball-reference.com{slug}')
        if r is None or r.status_code != 200:
            print(f"    -> Status {r.status_code if r else 'None'}")
            continue

        try:
            soup = BeautifulSoup(r.content, 'html.parser')
            row, err = fetch_stats_row(soup)
            if err:
                print(f"    -> {err}")
                continue

            height, birthday = parse_bio(soup)
            if not height or not birthday:
                print(f"    -> WARNING: couldn't parse bio (height={height!r}, birthday={birthday!r})")

            entry = {
                'TEAM': team_name,
                'HEIGHT': height,
                'BIRTHDAY': birthday,
                'NAME': name,
                'SLUG': slug,
                'PPG': round(float(row['PTS'].values[0]), 1),
                'RPG': round(float(row['TRB'].values[0]), 1),
                'APG': round(float(row['AST'].values[0]), 1),
            }
            stats[slug] = entry
            print(f"    -> {entry['PPG']} PPG, {entry['RPG']} RPG, {entry['APG']} APG")
            with open('data/roster_stats.json', 'w') as f:
                json.dump(stats, f, indent=4)
        except KeyboardInterrupt:
            with open('data/roster_stats.json', 'w') as f:
                json.dump(stats, f, indent=4)
            print(f"\nInterrupted — saved")
            sys.exit(0)
        except Exception as e:
            print(f"    -> Error: {e}")
            continue

        sleep(random.uniform(6, 14))

def slug_id(slug):
    return slug.split('/')[-1].replace('.html', '')

final = {slug_id(slug): info for slug, info in stats.items() if 'PPG' in info}
with open('players.json', 'w') as f:
    json.dump(final, f, indent=4)
print(f"\nDone — {len(final)} players saved to players.json")
