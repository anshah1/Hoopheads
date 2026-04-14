from data.sportradar_apikey import get_key
import requests
import json
import time

headers = {
    "accept": "application/json",
    "x-api-key": get_key()
}

validTeams = ["Celtics", "Nets", "Knicks", "76ers", "Raptors", "Bulls", "Cavaliers", "Pistons", "Pacers", "Bucks", "Hawks", "Hornets", "Heat", "Magic", "Wizards", "Nuggets", "Timberwolves", "Thunder", "Trail Blazers", "Jazz", "Warriors", "Clippers", "Lakers", "Suns", "Kings", "Mavericks", "Rockets", "Grizzlies", "Pelicans", "Spurs"]

# Step 1: Fetch all teams and filter to 30 valid NBA teams
teamsURL = "https://api.sportradar.com/nba/trial/v8/en/league/teams.json"
teams = requests.get(teamsURL, headers=headers).json()['teams']
with open('data/teams.json', 'w') as file:
    json.dump(teams, file, indent=4)

teams = json.load(open('data/teams.json', 'r'))
i = 0
while i < len(teams):
    if teams[i]['name'] not in validTeams:
        print(f"Removing {teams[i]['name']} from teams.json")
        teams.pop(i)
    else:
        i += 1

print(f"Found {len(teams)} valid teams")

def formatHeight(inches):
    feet = inches // 12
    remaining = inches % 12
    return f"{feet}-{remaining}"

# Step 2: Fetch each team's roster and build player list
allPlayers = {}
for team in teams:
    teamURL = f"https://api.sportradar.com/nba/trial/v8/en/teams/{team['id']}/profile.json"
    teamProfile = requests.get(teamURL, headers=headers).json()
    print(f"Processing team: {team['name']}")
    for player in teamProfile['players']:
        try:
            allPlayers[player['full_name']] = {}
            allPlayers[player['full_name']]['ID'] = player['id']
            allPlayers[player['full_name']]['TEAM'] = team['name']
            allPlayers[player['full_name']]['HEIGHT'] = formatHeight(player['height'])
            allPlayers[player['full_name']]['BIRTHDAY'] = player['birthdate']
        except Exception as e:
            print(f"Error processing player {player.get('full_name', 'unknown')}: {e}")
            continue
        time.sleep(1)
    time.sleep(2)

with open('data/players.json', 'w') as file:
    json.dump(allPlayers, file, indent=4)

print(f"Saved {len(allPlayers)} players to data/players.json")

# Step 3: Fetch per-player stats for the 2025-26 season
players = json.load(open('data/players.json', 'r'))
for player, playerInfo in players.items():
    url = f"https://api.sportradar.com/nba/trial/v8/en/players/{playerInfo['ID']}/profile.json"
    try:
        playerProfile = requests.get(url, headers=headers).json()
        for season in playerProfile.get('seasons', []):
            if season['year'] == 2026 and season['type'] == 'REG':
                totalGames = 0
                totalPoints = 0
                totalAssists = 0
                totalRebounds = 0
                for team in season['teams']:
                    totalGames += team['total']['games_played']
                    totalPoints += team['total']['points']
                    totalAssists += team['total']['assists']
                    totalRebounds += team['total']['rebounds']
                if totalGames >= 30:
                    playerInfo['PPG'] = round(totalPoints / totalGames, 1)
                    playerInfo['APG'] = round(totalAssists / totalGames, 1)
                    playerInfo['RPG'] = round(totalRebounds / totalGames, 1)
                    print(f"{player}: {playerInfo['PPG']} PPG, {playerInfo['RPG']} RPG, {playerInfo['APG']} APG")
        time.sleep(2)
    except KeyboardInterrupt:
        with open('data/players.json', 'w') as file:
            json.dump(players, file, indent=4)
        print("Interrupted — partial data saved.")
        break
    except Exception as e:
        print(f"Error processing player {player}: {e}")
        with open('data/players.json', 'w') as file:
            json.dump(players, file, indent=4)
        continue

with open('data/players.json', 'w') as file:
    json.dump(players, file, indent=4)

print("Stats updated in data/players.json")

# Step 4: Remove players missing stats, save final to root players.json
newPlayers = {}
for player, info in players.items():
    if 'PPG' in info and 'APG' in info and 'RPG' in info:
        newPlayers[player] = info

with open('data/players.json', 'w') as file:
    json.dump(newPlayers, file, indent=4)

with open('players.json', 'w') as file:
    json.dump(newPlayers, file, indent=4)

print(f"Final cleaned data: {len(newPlayers)} players saved to data/players.json and players.json")
