from bs4 import BeautifulSoup
from requests import get
from time import sleep
import unidecode, unicodedata
import pandas as pd
import json
import sys

# Usage:
#   python scrape_bref.py           -- run all steps
#   python scrape_bref.py --step2   -- skip step 1, use existing data/bref_bio.json
#   python scrape_bref.py --step3   -- skip steps 1 & 2, use existing data/bref_bio.json

step = 1
if '--step2' in sys.argv:
    step = 2
elif '--step3' in sys.argv:
    step = 3

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.basketball-reference.com/',
}

TEAMS = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BRK',
    'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
    'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
    'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
    'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHO',
    'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
    'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
}

def bref_get(url):
    r = get(url, headers=HEADERS, timeout=15)
    while r.status_code == 429:
        print("  Rate limited, waiting 5s...")
        sleep(5)
        r = get(url, headers=HEADERS, timeout=15)
    return r

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
        if r.status_code == 404:
            return None
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            h1 = soup.find('h1')
            if not h1:
                return None
            page_name = unidecode.unidecode(h1.find('span').text).lower()
            if page_name == normalized.lower():
                return suffix
            # increment player number and retry
            num = int(''.join(c for c in suffix if c.isdigit())) + 1
            num_str = f"0{num}" if num < 10 else str(num)
            suffix = f'/players/{initial}/{last_part}{first_part}{num_str}.html'
    return None

# Step 1: scrape all team rosters from bref
if step <= 1:
    print("--- Step 1: Fetching rosters from bref ---")
    bio = {}
    for team_name, abbr in TEAMS.items():
        url = f'https://www.basketball-reference.com/teams/{abbr}/2025.html'
        print(f"  {team_name}...")
        r = bref_get(url)
        if r.status_code != 200:
            print(f"  Failed: {r.status_code}")
            continue
        soup = BeautifulSoup(r.content, 'html.parser')
        roster_table = soup.find('table', {'id': 'roster'})
        if not roster_table:
            print(f"  No roster table found")
            continue
        rows = roster_table.find('tbody').find_all('tr')
        for row in rows:
            try:
                name_cell = row.find('td', {'data-stat': 'player'})
                height_cell = row.find('td', {'data-stat': 'height'})
                bday_cell = row.find('td', {'data-stat': 'birth_date'})
                if not name_cell:
                    continue
                name = name_cell.text.strip()
                height = height_cell.text.strip().replace('-', '-') if height_cell else ''
                birthday = bday_cell.find('a').text.strip() if bday_cell and bday_cell.find('a') else ''
                # convert birthday from "Month DD, YYYY" to YYYY-MM-DD
                from datetime import datetime
                try:
                    birthday = datetime.strptime(birthday, '%B %d, %Y').strftime('%Y-%m-%d')
                except:
                    pass
                bio[name] = {
                    'TEAM': team_name.split(' ')[-1],  # just last word e.g. "Hawks"
                    'HEIGHT': height,
                    'BIRTHDAY': birthday
                }
            except Exception as e:
                continue
        print(f"  Got {len(rows)} rows, {len(bio)} total players so far")
        with open('data/bref_bio.json', 'w') as f:
            json.dump(bio, f, indent=4)
        sleep(4)
    print(f"Step 1 done — {len(bio)} players in data/bref_bio.json")
else:
    bio = json.load(open('data/bref_bio.json'))
    print(f"Loaded {len(bio)} players from data/bref_bio.json")

# Step 2 & 3: get stats for each player
print(f"\n--- Step 2: Fetching stats for {len(bio)} players ---")
try:
    stats = json.load(open('data/bref_stats.json'))
except FileNotFoundError:
    stats = {}

already_done = set(p for p, info in stats.items() if 'PPG' in info)
print(f"{len(already_done)} already have stats")

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
    if r.status_code != 200:
        print(f"  -> Status {r.status_code}")
        continue

    try:
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find('table', {'id': 'per_game'})
        if not table:
            print(f"  -> No per_game table")
            continue
        df = pd.read_html(str(table))[0]
        # get 2024-25 season row
        row = df[df['Season'] == '2024-25']
        if row.empty:
            # try most recent non-Career row
            df = df[df['Season'] != 'Career']
            row = df.dropna(subset=['Season']).tail(1)
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
    except KeyboardInterrupt:
        with open('data/bref_stats.json', 'w') as f:
            json.dump(stats, f, indent=4)
        print(f"\nInterrupted at [{i+1}/{len(bio)}] — saved")
        sys.exit(0)
    except Exception as e:
        print(f"  -> Error: {e}")

    with open('data/bref_stats.json', 'w') as f:
        json.dump(stats, f, indent=4)
    sleep(4)

final = {p: info for p, info in stats.items() if 'PPG' in info and 'RPG' in info and 'APG' in info}
with open('players.json', 'w') as f:
    json.dump(final, f, indent=4)
print(f"\nDone — {len(final)} players saved to players.json")
