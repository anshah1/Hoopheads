from nba_api.stats.static import teams as nba_teams, players as nba_players
from nba_api.stats.endpoints import commonteamroster, commonplayerinfo
import json
import time
import sys

# Usage:
#   python scrape_nbaapi.py           -- run all steps
#   python scrape_nbaapi.py --step2   -- skip step 1, use existing data/nba_bio.json
#   python scrape_nbaapi.py --step3   -- skip steps 1 & 2, use existing data/nba_bio.json

step = 1
if '--step2' in sys.argv:
    step = 2
elif '--step3' in sys.argv:
    step = 3

# Step 1: get all team rosters
if step <= 1:
    print("--- Step 1: Fetching rosters from nba_api ---")
    all_teams = nba_teams.get_teams()
    bio = {}
    for i, team in enumerate(all_teams):
        print(f"[{i+1}/{len(all_teams)}] {team['full_name']}...")
        try:
            roster = commonteamroster.CommonTeamRoster(team_id=team['id'], season='2024-25', timeout=30)
            players = roster.get_normalized_dict()['CommonTeamRoster']
            for p in players:
                bio[p['PLAYER']] = {
                    'NBA_ID': p['PLAYER_ID'],
                    'TEAM': team['nickname'],
                    'HEIGHT': p.get('HEIGHT', ''),
                    'BIRTHDAY': p.get('BIRTH_DATE', '')[:10] if p.get('BIRTH_DATE') else ''
                }
            print(f"  Got {len(players)} players")
        except KeyboardInterrupt:
            with open('data/nba_bio.json', 'w') as f:
                json.dump(bio, f, indent=4)
            print("Interrupted — saved")
            sys.exit(0)
        except Exception as e:
            print(f"  Error: {e}")
        with open('data/nba_bio.json', 'w') as f:
            json.dump(bio, f, indent=4)
        time.sleep(1)
    print(f"Step 1 done — {len(bio)} players in data/nba_bio.json")
else:
    bio = json.load(open('data/nba_bio.json'))
    print(f"Loaded {len(bio)} players from data/nba_bio.json")

# Step 2: get stats for each player
print(f"\n--- Step 2: Fetching stats for {len(bio)} players ---")
try:
    stats = json.load(open('data/nba_stats.json'))
except FileNotFoundError:
    stats = {}

already_done = set(p for p, info in stats.items() if 'PPG' in info)
print(f"{len(already_done)} already have stats")

for i, (name, info) in enumerate(bio.items()):
    if name in already_done:
        print(f"[{i+1}/{len(bio)}] {name} — skipping")
        continue

    print(f"[{i+1}/{len(bio)}] {name}...")
    try:
        player_id = info.get('NBA_ID')
        if not player_id:
            matches = nba_players.find_players_by_full_name(name)
            if not matches:
                print(f"  -> Not found")
                continue
            player_id = matches[0]['id']

        data = commonplayerinfo.CommonPlayerInfo(player_id=player_id, timeout=30)
        headline = data.get_normalized_dict()['PlayerHeadlineStats'][0]

        entry = dict(info)
        entry['PPG'] = headline['PTS']
        entry['RPG'] = headline['REB']
        entry['APG'] = headline['AST']
        stats[name] = entry
        print(f"  -> {entry['PPG']} PPG, {entry['RPG']} RPG, {entry['APG']} APG")

    except KeyboardInterrupt:
        with open('data/nba_stats.json', 'w') as f:
            json.dump(stats, f, indent=4)
        print(f"\nInterrupted at [{i+1}/{len(bio)}] — saved")
        sys.exit(0)
    except Exception as e:
        print(f"  -> Error: {e}")

    with open('data/nba_stats.json', 'w') as f:
        json.dump(stats, f, indent=4)
    time.sleep(0.6)

final = {p: info for p, info in stats.items() if 'PPG' in info and 'RPG' in info and 'APG' in info}
with open('players.json', 'w') as f:
    json.dump(final, f, indent=4)
print(f"\nDone — {len(final)} players saved to players.json")
