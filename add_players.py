from bs4 import BeautifulSoup
from io import StringIO
import requests
import pandas as pd
import json
import re

# bref's per_game_stats "Team" column uses these abbreviations; our data uses nicknames
TEAM_ABBR_TO_NICKNAME = {
    'ATL': 'Hawks', 'BOS': 'Celtics', 'BRK': 'Nets', 'CHO': 'Hornets', 'CHI': 'Bulls',
    'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets', 'DET': 'Pistons', 'GSW': 'Warriors',
    'HOU': 'Rockets', 'IND': 'Pacers', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MEM': 'Grizzlies',
    'MIA': 'Heat', 'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks',
    'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHO': 'Suns', 'POR': 'Trail Blazers',
    'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors', 'UTA': 'Jazz', 'WAS': 'Wizards',
}

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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.basketball-reference.com/',
}

# name in game -> bref URL
MANUAL_PLAYERS = {
    'Bub Carrington':   'https://www.basketball-reference.com/players/c/carrica01.html',
    'Jimmy Butler':     'https://www.basketball-reference.com/players/b/butleji01.html',
    'Robert Williams':  'https://www.basketball-reference.com/players/w/williro04.html',
    'Yang Hansen':      'https://www.basketball-reference.com/players/y/yangha01.html',
    'Jalen Williams':   'https://www.basketball-reference.com/players/w/willija06.html',
    'Jaylin Williams':  'https://www.basketball-reference.com/players/w/willija07.html',
    'Mark Williams':    'https://www.basketball-reference.com/players/w/willima07.html',
    "Royce O'Neale":   'https://www.basketball-reference.com/players/o/onealro01.html',
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

try:
    stats = json.load(open('data/bref_stats.json'))
except FileNotFoundError:
    stats = {}

total = len(MANUAL_PLAYERS)

for i, (name, url) in enumerate(MANUAL_PLAYERS.items()):
    print(f"[{i+1}/{total}] {name}...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  -> Status {r.status_code}")
            continue

        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find('table', {'id': 'per_game_stats'})
        if not table:
            print(f"  -> No per_game_stats table")
            continue

        df = pd.read_html(StringIO(str(table)))[0]
        row = df[df['Season'] == '2025-26']
        if row.empty:
            print(f"  -> No 2025-26 row, seasons: {df['Season'].tolist()}")
            continue

        games = int(row['G'].values[0])
        if games < 30:
            print(f"  -> Only {games} games, skipping")
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
            'SLUG': url.replace('https://www.basketball-reference.com', ''),
            'PPG': round(float(row['PTS'].values[0]), 1),
            'RPG': round(float(row['TRB'].values[0]), 1),
            'APG': round(float(row['AST'].values[0]), 1),
        }
        stats[name] = entry
        print(f"  -> {entry['PPG']} PPG, {entry['RPG']} RPG, {entry['APG']} APG ({games} games)")

        with open('data/bref_stats.json', 'w') as f:
            json.dump(stats, f, indent=4)

    except Exception as e:
        print(f"  -> Error: {e}")
        continue

print(f"\nDone — {len(stats)} total players in bref_stats.json")
