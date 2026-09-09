from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from io import StringIO
from time import sleep
from zoneinfo import ZoneInfo
import re
import pandas as pd
import requests
import socks, socket
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
SEASON_YEAR = 2026
MIN_GAMES_SHARE = 0.38  # must have played this share of their current team's games so far

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

def get_teams_that_played(date):
    """Team abbreviations with a game on this date, via the boxscores-by-date page."""
    url = f'https://www.basketball-reference.com/boxscores/?month={date.month}&day={date.day}&year={date.year}'
    r = bref_get(url)
    if r is None or r.status_code != 200:
        return set()

    soup = BeautifulSoup(r.content, 'html.parser')
    teams = set()
    for link in soup.find_all('a', href=re.compile(r'^/teams/[A-Z]{3}/\d{4}\.html$')):
        teams.add(link['href'].split('/')[2])
    return teams

def get_traded_players_on(date):
    """[(name, slug), ...] for every player mentioned in that date's transactions."""
    url = f'https://www.basketball-reference.com/leagues/NBA_{SEASON_YEAR}_transactions.html'
    r = bref_get(url)
    if r is None or r.status_code != 200:
        return []

    date_str = date.strftime('%B ') + str(date.day) + date.strftime(', %Y')  # e.g. "January 9, 2026" — no zero-padded day
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.find('div', id='content')
    if not content:
        return []

    for li in content.find_all('li'):
        span = li.find('span')
        if span and span.get_text().strip() == date_str:
            return [(a.text.strip(), a['href']) for a in li.find_all('a', href=re.compile(r'^/players/'))]
    return []

def get_roster(team_abbr):
    """[(name, slug), ...] for a team's current roster."""
    url = f'https://www.basketball-reference.com/teams/{team_abbr}/{SEASON_YEAR}.html'
    r = bref_get(url)
    if r is None or r.status_code != 200:
        return []

    soup = BeautifulSoup(r.content, 'html.parser')
    table = soup.find('table', id='roster')
    if not table:
        return []

    roster = []
    for row in table.find('tbody').find_all('tr'):
        cell = row.find('td', {'data-stat': 'player'})
        if not cell:
            continue
        link = cell.find('a')
        if link and link.get('href'):
            roster.append((link.text.strip(), link['href']))
    return roster

def get_team_games_played(team_abbr):
    """How many games this team has completed so far this season."""
    url = f'https://www.basketball-reference.com/teams/{team_abbr}/{SEASON_YEAR}_games.html'
    r = bref_get(url)
    if r is None or r.status_code != 200:
        return None

    soup = BeautifulSoup(r.content, 'html.parser')
    table = soup.find('table', id='games')
    if not table:
        return None

    completed = 0
    for row in table.find('tbody').find_all('tr'):
        result_cell = row.find('td', {'data-stat': 'game_result'})
        if result_cell and result_cell.get_text().strip():
            completed += 1
    return completed

def get_player_season_stats(slug):
    """Returns (current_team_abbr, total_games, ppg, rpg, apg) for this season, combining
    multiple stints if the player was traded — bref's own 'XTM' row already sums this up."""
    r = bref_get(f'https://www.basketball-reference.com{slug}')
    if r is None or r.status_code != 200:
        return None, f"status {r.status_code if r else 'None'}"

    soup = BeautifulSoup(r.content, 'html.parser')
    table = soup.find('table', {'id': 'per_game_stats'})
    if not table:
        return None, "no per_game table"

    df = pd.read_html(StringIO(str(table)))[0]
    season_rows = df[df['Season'] == SEASON]
    if season_rows.empty:
        return None, f"no {SEASON} row"

    # multi-team row (e.g. "2TM") comes first when present and already sums games/stats;
    # the current team is whichever single-team row is listed LAST (most recent stint)
    combined_row = season_rows[season_rows['Team'].str.contains(r'^\dTM$', regex=True)]
    stats_row = combined_row.iloc[0] if not combined_row.empty else season_rows.iloc[0]
    single_team_rows = season_rows[~season_rows['Team'].str.contains(r'^\dTM$', regex=True)]
    current_team_abbr = single_team_rows.iloc[-1]['Team'] if not single_team_rows.empty else stats_row['Team']

    return {
        'team_abbr': current_team_abbr,
        'games': int(stats_row['G']),
        'ppg': round(float(stats_row['PTS']), 1),
        'rpg': round(float(stats_row['TRB']), 1),
        'apg': round(float(stats_row['AST']), 1),
    }, None

def parse_bio(soup):
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

def slug_id(slug):
    return slug.split('/')[-1].replace('.html', '')
