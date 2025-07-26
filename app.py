import random
import os
import sys
import warnings
import sqlite3
from io import StringIO
from flask import Flask, redirect, render_template, session, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from data.dataStorage import divisions, players, allTheData, divisionBreakdown
warnings.simplefilter(action='ignore', category=FutureWarning)
from datetime import datetime, timedelta
from scraper.players import get_player_headshot, get_player_link
from dotenv import load_dotenv
load_dotenv()
import unicodedata
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = True
app.permanent_session_lifetime = timedelta(minutes=30)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-temp-secret")

matches = [
    [1, 'ones'],
    [2, 'two'],
    [3, 'three'],
    [4, 'four'],
    [5, 'five'],
    [6, 'six'],
    [7, 'sevens'],
    [8, 'eights']
]

# Setup SQLite database connection
import sqlite3
def get_db_connection():
    conn = sqlite3.connect("Hoopheads.db")
    cur = conn.cursor()
    return {'connection': conn, 'cursor': cur}

@app.route("/", methods=["GET"])
def start_game():
    session.permanent = True
    player_found = False
    while not player_found:
        random_player = random.choice(allTheData)
        print(f"Selected Player: {random_player['NAME']}")
        try:
            ppg = float(random_player['PPG'])
            rpg = float(random_player['RPG'])
            apg = float(random_player['APG'])
            player_found = True
        except:
            continue  # skip malformed player

    session["correct_player"] = random_player["NAME"]
    session["ppg"] = ppg
    session["apg"] = apg
    session["rpg"] = rpg
    session["division"] = defaultDivision(random_player)
    height = random_player["HEIGHT"]
    session["inches"] = int(height[0]) * 12 + int(height[2])
    session["age"] = defaultAge(random_player['NAME'])
    session["guess_count"] = 0
    session["guesses"] = [{"name": "", "division": "", "height": "", "age": ""} for _ in range(8)]
    return render_template("index.html", ppg=ppg, apg=apg, rpg=rpg, guesses=session["guesses"])

@app.route("/guess", methods=["POST"])
def process_guess():
    guessedPlayer = request.form.get("player-search")
    print(f'Guessed player: {guessedPlayer}')
    ppg = session.get("ppg")
    apg = session.get("apg")
    rpg = session.get("rpg")
    guesses = session.get("guesses", [{"name": "", "division": "", "divColor": "", "height": "", "ppg": "", "rpg": "", "apg": "","divColor": "", "age": ""} for _ in range(8)])
    guess_count = session.get("guess_count", 0) + 1
    session["guess_count"] = guess_count

    image_url = get_player_headshot(session["correct_player"])
    print(f"Player Image URL: {image_url}")
    if image_url is None:
        image_url = "https://www.logodesignlove.com/images/classic/nba-logo.jpg"

    player_link = get_player_link(session["correct_player"])
    print(f"Player Link: {player_link}")

    if session["correct_player"] == guessedPlayer:
        return render_template("congrats.html", player_name=session["correct_player"], guess_count=guess_count, image_url=image_url, player_link = player_link)
    else:
        if session["guess_count"] == 8:
            return render_template("failure.html", player_name = session["correct_player"], image_url=image_url, player_link = player_link)
        guesses[guess_count - 1]["name"] = guessedPlayer
        guesses[guess_count-1]['division'] = getDivision(guessedPlayer)[0]
        guesses[guess_count-1]['divColor'] = getDivision(guessedPlayer)[1]
        guesses[guess_count - 1]["height"] = getHeight(guessedPlayer)
        guesses[guess_count - 1]["ppg"] = getPoints(guessedPlayer)
        guesses[guess_count - 1]["rpg"] = getRebounds(guessedPlayer)
        guesses[guess_count - 1]["apg"] = getAssists(guessedPlayer)
        guesses[guess_count - 1]["age"] = getAge(guessedPlayer)
        return render_template("index.html", ppg=ppg, apg=apg, rpg=rpg, guesses = guesses)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').lower()
    def strip_accents(text):
        return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

    if query:
        norm_query = strip_accents(query)
        matches = [player for player in players if norm_query in strip_accents(player.lower())]
        return jsonify(matches[:10])
    return jsonify([])

def getDivision(guessedPlayer):
    for player in allTheData:
        if player['NAME'] == guessedPlayer:
            division = defaultDivision(player)
            if division == session["division"]:
                return [division, "#90EE90"]
            else:
                for conference in divisionBreakdown:
                    if division in conference and session["division"] in conference:
                        return [division, "#FFFFC5"]
                return [division, "#FFCCCB"]

            
def getHeight(guessedPlayer):
    for player in allTheData:
        if player['NAME'] == guessedPlayer:
            height = player['HEIGHT']
            if len(height) == 4:
                inches = inches = int(height[0]) * 12 + int(height[2]) * 10 + int(height[3])
            else:
                inches = int(height[0]) * 12 + int(height[2])
            if session["inches"] > inches:
                if session["inches"] - inches == 1 or session["inches"] - inches == 2:
                    return [height, 'closeup']
                return [height, 'up']
            elif session["inches"] < inches:
                if inches - session["inches"] == 1 or inches - session["inches"] == 2:
                    return [height, 'closedown']
                return [height, 'down']
            else:
                return [height, 'equal']

def getPoints(guessedPlayer):
    for player in allTheData:
        if player['NAME'] == guessedPlayer:
            return player['PPG']
        
def getRebounds(guessedPlayer):
    for player in allTheData:
        if player['NAME'] == guessedPlayer:
            return player['RPG']
        
def getAssists(guessedPlayer):
    for player in allTheData:
        if player['NAME'] == guessedPlayer:
            return player['APG']
        
def getAge(guessedPlayer):
    age = defaultAge(guessedPlayer)
    if session["age"] > age:
        if session["age"] - age == 1 or session["age"] - age == 2:
            return [age, 'closeup']
        return [age, 'up']
    elif session["age"] < age:
        if age - session["age"] == 1 or age - session["age"] == 2:
            return [age, 'closedown']
        return [age, 'down']
    else:
        return [age, 'equal']

def defaultDivision(player):
    for row in divisions:
        if player['TEAM'] in row:
            return row[0]
        
def defaultAge(player):
    for row in allTheData:
        if player == row['NAME']:
            bday_str = row['BIRTHDAY']
    bday = datetime.strptime(bday_str, "%Y-%m-%d")  # Adjust format if needed
    age = (datetime.today() - bday).days // 365
    return age


if __name__ == "__main__":
    app.run()
