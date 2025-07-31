from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo
import time

#this is outdated because i no longer structure the data in this way. when rescraping/autoscraping, i need to update

# Used the following function to get a list of players who scored 6+ ppg, in an attempt to put all relevant players and leave out "unknown" players from the game
def get_players_who_meet_threshold():
    player_names = []
    all_players = players.get_active_players()
    for player in all_players:
        player_id = player['id']
        try:
            info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            full_name = info.get_normalized_dict()['CommonPlayerInfo'][0]['DISPLAY_FIRST_LAST']
            ppg = info.get_normalized_dict()['PlayerHeadlineStats'][0]['PTS']
            if ppg >=6:
                print(f"Player ID: {player_id}, Name: {full_name}, PPG: {ppg}")
                player_names.append(full_name)
            time.sleep(0.5)
        except Exception as e:
            print(f"Error retrieving data for player ID {player_id}: {e}")
    return player_names

# Call the function to get players with PPG greater than 6
allPlayers = get_players_who_meet_threshold()

# Used the following function to get all the information need for the game, appending it to a list of dictionaries
def getFullData(allPlayers):
    fullData = []
    for player in allPlayers:
        playerData = {}
        try:
            player_id = players.find_players_by_full_name(player)[0]['id']
            info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            playerData['name'] = info.get_normalized_dict()['CommonPlayerInfo'][0]['DISPLAY_FIRST_LAST']
            playerData['ppg'] = info.get_normalized_dict()['PlayerHeadlineStats'][0]['PTS']
            playerData['rpg'] = info.get_normalized_dict()['PlayerHeadlineStats'][0]['REB']
            playerData['apg'] = info.get_normalized_dict()['PlayerHeadlineStats'][0]['AST']
            playerData['team'] = info.get_normalized_dict()['CommonPlayerInfo'][0]['TEAM_NAME']
            playerData['height'] = info.get_normalized_dict()['CommonPlayerInfo'][0]['HEIGHT']
            playerData['bday'] = info.get_normalized_dict()['CommonPlayerInfo'][0]['BIRTHDATE']
            time.sleep(0.5)  # To respect rate limits
            print(f"Player ID: {player_id}, Name: {playerData['name']}")
            fullData.append(playerData)
        except Exception as e:
            print(f"Error retrieving data for player {player['id']}: {e}")
            continue
    return fullData

# Call the function to get full data for all players
fullData = getFullData(allPlayers)

#Used the following function to sort the players list, hence the search suggestions, by descending alphabetical

#Call the function to sort the players list
allPlayersSorted = sort(allPlayers, fullData)