from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo
import time

# Used the following function to get a list of players who scored 6+ ppg, in an attempt to put all relevant players and leave out "unknown" players from the game
def get_players_with_ppg_greater_than_6():
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
allPlayers = get_players_with_ppg_greater_than_6()

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

#Used the following function to sort the players list, hence the search suggestions, by descending ppg, putting more relevant players higher
def selectionSort(array, allTheData):
    swapCount = 0
    size = len(array)
    for ind in range(size):
        for row in allTheData:
            if row['NAME'] == array[ind]:
                I_ppg = row['PPG']
        for j in range(ind + 1, size):
            for row in allTheData:
                if row['NAME'] == array[j]:
                    J_ppg = row['PPG']
            if J_ppg > I_ppg:
                min_index = j
                I_ppg = J_ppg

        array[ind], array[min_index] = array[min_index], array[ind]
        swapCount += 1
        print(f"Swapped {array[ind]} with {array[min_index]}")

    return array

#Call the function to sort the players list
allPlayersSorted = selectionSort(allPlayers, fullData)