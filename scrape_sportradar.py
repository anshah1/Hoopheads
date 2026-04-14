from data.sportradar_apikey import get_key
import requests
import json
import time
import sys

# Usage:
#   python scrape_sportradar.py           -- run all steps
#   python scrape_sportradar.py --step2   -- skip step 1, use existing data/sr_teams.json
#   python scrape_sportradar.py --step3   -- skip steps 1 & 2, use existing data/sr_bio.json

step = 1
if '--step2' in sys.argv:
    step = 2
elif '--step3' in sys.argv:
    step = 3

headers = {
    "accept": "application/json",
    "x-api-key": get_key()
}

validTeams = ["Celtics", "Nets", "Knicks", "76ers", "Raptors", "Bulls", "Cavaliers", "Pistons", "Pacers", "Bucks", "Hawks", "Hornets", "Heat", "Magic", "Wizards", "Nuggets", "Timberwolves", "Thunder", "Trail Blazers", "Jazz", "Warriors", "Clippers", "Lakers", "Suns", "Kings", "Mavericks", "Rockets", "Grizzlies", "Pelicans", "Spurs"]

def formatHeight(inches):
    feet = inches // 12
    remaining = inches % 12
    return f"{feet}-{remaining}"

# Step 1: fetch and filter teams
if step <= 1:
    print("--- Step 1: Fetching teams ---")
    r = requests.get("https://api.sportradar.com/nba/trial/v8/en/league/teams.json", headers=headers)
    print(f"Status: {r.status_code}")
    if r.status_code != 200:
        print(f"Error: {r.text[:300]}")
        sys.exit(1)
    teams = r.json()['teams']
    teams = [t for t in teams if t['name'] in validTeams]
    with open('data/sr_teams.json', 'w') as f:
        json.dump(teams, f, indent=4)
    print(f"Saved {len(teams)} teams to data/sr_teams.json")
else:
    teams = json.load(open('data/sr_teams.json'))
    print(f"Loaded {len(teams)} teams from data/sr_teams.json")

# Step 2: fetch rosters and build bio file
if step <= 2:
    print("\n--- Step 2: Fetching rosters ---")
    bio = {}
    for team in teams:
        url = f"https://api.sportradar.com/nba/trial/v8/en/teams/{team['id']}/profile.json"
        r = requests.get(url, headers=headers)
        print(f"  {team['name']} — status {r.status_code}")
        if r.status_code == 429:
            print("  Rate limited, waiting 10s...")
            time.sleep(10)
            r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"  Failed: {r.text[:200]}")
            continue
        for player in r.json()['players']:
            try:
                bio[player['full_name']] = {
                    'ID': player['id'],
                    'TEAM': team['name'],
                    'HEIGHT': formatHeight(player['height']),
                    'BIRTHDAY': player['birthdate']
                }
            except Exception as e:
                print(f"  Error on {player.get('full_name', '?')}: {e}")
        with open('data/sr_bio.json', 'w') as f:
            json.dump(bio, f, indent=4)
        print(f"  Saved {len(bio)} players so far")
        time.sleep(2)
    print(f"Step 2 done — {len(bio)} players in data/sr_bio.json")
else:
    bio = json.load(open('data/sr_bio.json'))
    print(f"Loaded {len(bio)} players from data/sr_bio.json")

# Step 3: fetch stats
print(f"\n--- Step 3: Fetching stats for {len(bio)} players ---")
try:
    stats = json.load(open('data/sr_stats.json'))
except FileNotFoundError:
    stats = {}

already_done = set(p for p, info in stats.items() if 'PPG' in info)
print(f"{len(already_done)} players already have stats, skipping them")

for i, (name, info) in enumerate(bio.items()):
    if name in already_done:
        print(f"[{i+1}/{len(bio)}] {name} — already done, skipping")
        continue

    url = f"https://api.sportradar.com/nba/trial/v8/en/players/{info['ID']}/profile.json"
    print(f"[{i+1}/{len(bio)}] {name}...")

    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 429:
            print("  Rate limited, waiting 10s...")
            time.sleep(10)
            r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"  !! Status {r.status_code} — skipping")
            continue

        profile = r.json()
        entry = dict(info)
        all_seasons = [(s['year'], s['type']) for s in profile.get('seasons', [])]
        print(f"  Seasons: {all_seasons}")

        for season in profile.get('seasons', []):
            if season['year'] == 2025 and season['type'] == 'REG':
                total_games = total_pts = total_ast = total_reb = 0
                for team in season['teams']:
                    total_games += team['total']['games_played']
                    total_pts += team['total']['points']
                    total_ast += team['total']['assists']
                    total_reb += team['total']['rebounds']
                if total_games >= 30:
                    entry['PPG'] = round(total_pts / total_games, 1)
                    entry['RPG'] = round(total_reb / total_games, 1)
                    entry['APG'] = round(total_ast / total_games, 1)
                    print(f"  -> {entry['PPG']} PPG, {entry['RPG']} RPG, {entry['APG']} APG ({total_games} games)")
                else:
                    print(f"  -> Only {total_games} games, skipping")

        stats[name] = entry
        with open('data/sr_stats.json', 'w') as f:
            json.dump(stats, f, indent=4)
        time.sleep(3)

    except KeyboardInterrupt:
        with open('data/sr_stats.json', 'w') as f:
            json.dump(stats, f, indent=4)
        print(f"\nInterrupted at [{i+1}/{len(bio)}] — data/sr_stats.json saved")
        sys.exit(0)
    except Exception as e:
        print(f"  !! Error: {e}")
        continue

# Step 4: filter and save final
final = {p: info for p, info in stats.items() if 'PPG' in info and 'RPG' in info and 'APG' in info}
with open('players.json', 'w') as f:
    json.dump(final, f, indent=4)
print(f"\nDone — {len(final)} players saved to players.json")
