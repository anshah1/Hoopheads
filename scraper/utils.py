from bs4 import BeautifulSoup
import pandas as pd
import unicodedata, unidecode
from .request_utils import get_wrapper


def get_game_suffix(date, team1, team2):
    r = get_wrapper(f'https://www.basketball-reference.com/boxscores/?month={date.month}&year={date.year}&day={date.day}')
    if r.status_code==200:
        soup = BeautifulSoup(r.content, 'html.parser')
        for table in soup.find_all('table', attrs={'class': 'teams'}):
            for anchor in table.find_all('a'):
                if 'boxscores' in anchor.attrs['href']:
                    if team1 in str(anchor.attrs['href']) or team2 in str(anchor.attrs['href']):
                        suffix = anchor.attrs['href']
                        return suffix
"""
    Helper function for inplace creation of suffixes--necessary in order
    to fetch rookies and other players who aren't in the /players
    catalogue. Added functionality so that players with abbreviated names
    can still have a suffix created.
"""
def create_last_name_part_of_suffix(potential_last_names):
    last_names = ''.join(potential_last_names)
    if len(last_names) <= 5:
        return last_names[:].lower()
    else:
        return last_names[:5].lower()

"""
    Amended version of the original suffix function--it now creates all
    suffixes in place.

    Since basketball reference standardizes URL codes, it is much more efficient
    to create them locally and compare names to the page results. The maximum
    amount of times a player code repeats is 5, but only 2 players have this
    problem--meaning most player URLs are correctly accessed within 1 to 2
    iterations of the while loop below.

    Added unidecode to make normalizing incoming string characters more
    consistent.

    This implementation dropped player lookup fail count from 306 to 35 to 0.
"""
def get_player_suffix(name):
    print(f"\n🔍 Starting suffix search for player name: {name}")

    normalized_name = unidecode.unidecode(unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode("utf-8"))
    print(f"➡️ Normalized name: {normalized_name}")

    if normalized_name == 'Metta World Peace':
        suffix = '/players/a/artesro01.html'
        print(f"🟢 Special case handled: {suffix}")
        return suffix
    elif normalized_name == 'KJ Martin':
        suffix = '/players/m/martike04.html'
        print(f"🟢 Special case handled: {suffix}")
        return suffix
    else:
        split_normalized_name = normalized_name.split(' ')
        if len(split_normalized_name) < 2:
            print("❌ Not enough name parts to construct suffix.")
            return None

        initial = split_normalized_name[1][0].lower()
        all_names = name.split(' ')
        first_name_part = unidecode.unidecode(all_names[0][:2].lower())
        first_name = all_names[0]
        other_names = all_names[1:]
        other_names_search = other_names[:]
        last_name_part = create_last_name_part_of_suffix(other_names)
        suffix = f'/players/{initial}/{last_name_part}{first_name_part}01.html'

        print(f"🔧 Constructed initial suffix: {suffix}")

    player_r = get_wrapper(f'https://www.basketball-reference.com{suffix}')
    print(f"🌐 Initial request status code: {player_r.status_code}")

    # Retry if 404
    while player_r.status_code == 404 and other_names_search:
        print(f"🔁 404 error - trying next name combination. Remaining: {other_names_search}")
        other_names_search.pop(0)
        last_name_part = create_last_name_part_of_suffix(other_names_search)
        initial = last_name_part[0].lower()
        suffix = f'/players/{initial}/{last_name_part}{first_name_part}01.html'
        print(f"➡️ Retrying with new suffix: {suffix}")
        player_r = get_wrapper(f'https://www.basketball-reference.com{suffix}')
        print(f"🌐 New request status code: {player_r.status_code}")

    while player_r.status_code == 200:
        player_soup = BeautifulSoup(player_r.content, 'html.parser')
        h1 = player_soup.find('h1')
        if h1:
            page_name = h1.find('span').text
            print(f"📄 Found player page title: {page_name}")

            if unidecode.unidecode(page_name).lower() == normalized_name.lower():
                print("✅ Exact name match found.")
                return suffix

            page_names = unidecode.unidecode(page_name).lower().split(' ')
            page_first_name = page_names[0]
            print(f"👥 Comparing with page first name: {page_first_name}")

            if first_name.lower() == page_first_name.lower():
                print("✅ First name match found. Not returning suffix.")
                #return suffix

            if first_name.lower()[:2] == page_first_name.lower()[:2]:
                print("🔁 Incrementing player number in suffix...")
                player_number = int(''.join(c for c in suffix if c.isdigit())) + 1
                if player_number < 10:
                    player_number = f"0{str(player_number)}"
                suffix = f"/players/{initial}/{last_name_part}{first_name_part}{player_number}.html"
                print(f"➡️ New incremented suffix: {suffix}")
            else:
                print("⚠️ Name mismatch. Trying alternative last name parts.")
                if other_names_search:
                    other_names_search.pop(0)
                    last_name_part = create_last_name_part_of_suffix(other_names_search)
                    initial = last_name_part[0].lower()
                    suffix = f'/players/{initial}/{last_name_part}{first_name_part}01.html'
                    print(f"➡️ Switching to new suffix: {suffix}")
                else:
                    print("❌ Ran out of name variations to try.")
                    return None

            player_r = get_wrapper(f'https://www.basketball-reference.com{suffix}')
            print(f"🌐 Rechecking new suffix status: {player_r.status_code}")
        else:
            print("❌ No <h1> tag found on player page.")
            return None

    print("❌ Final fallback: No match found.")
    return None


def remove_accents(name, team, season_end_year):
    alphabet = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXZY ')
    if len(set(name).difference(alphabet))==0:
        return name
    r = get_wrapper(f'https://www.basketball-reference.com/teams/{team}/{season_end_year}.html')
    team_df = None
    best_match = name
    if r.status_code==200:
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find('table')
        team_df = pd.read_html(str(table))[0]
        max_matches = 0
        for p in team_df['Player']:
            matches = sum(l1 == l2 for l1, l2 in zip(p, name))
            if matches>max_matches:
                max_matches = matches
                best_match = p
    return best_match
