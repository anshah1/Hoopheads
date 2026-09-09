from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from time import sleep
from zoneinfo import ZoneInfo
import re
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
