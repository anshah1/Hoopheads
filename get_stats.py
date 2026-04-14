from nba_api.stats.static import players as nba_players
from nba_api.stats.endpoints import commonplayerinfo
import json
import time

bio = json.load(open('data/players_bio.json', 'r'))

try:
    stats = json.load(open('data/players_stats.json', 'r'))
except FileNotFoundError:
    stats = {}

total = len(bio)
done = 0

print(f"Starting — {total} players to process")

for i, (name, info) in enumerate(bio.items()):
    print(f"[{i+1}/{total}] {name}...")

    matches = nba_players.find_players_by_full_name(name)
    if not matches:
        print(f"  -> Not found in nba_api, skipping")
        continue

    player_id = matches[0]['id']

    try:
        data = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        headline = data.get_normalized_dict()['PlayerHeadlineStats'][0]

        entry = dict(info)
        entry['PPG'] = headline['PTS']
        entry['RPG'] = headline['REB']
        entry['APG'] = headline['AST']

        stats[name] = entry
        print(f"  -> {entry['PPG']} PPG, {entry['RPG']} RPG, {entry['APG']} APG")
        done += 1

    except Exception as e:
        print(f"  -> Error: {e}")

    with open('data/players_stats.json', 'w') as f:
        json.dump(stats, f, indent=4)

    time.sleep(0.6)

print(f"\nDone — {done}/{total} players got stats")

# save final cleaned version to players.json
final = {p: info for p, info in stats.items() if 'PPG' in info and 'RPG' in info and 'APG' in info}
with open('players.json', 'w') as f:
    json.dump(final, f, indent=4)

print(f"Saved {len(final)} players to players.json")
