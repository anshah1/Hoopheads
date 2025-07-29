import random
import os
import warnings
import json
from io import StringIO
from flask import Flask, redirect, render_template, session, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from data.dataStorage import divisionBreakdown, conferenceBreakdown
warnings.simplefilter(action='ignore', category=FutureWarning)
from datetime import datetime, timedelta
from scraping import get_player_headshot, get_player_link
import unicodedata
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = True
app.permanent_session_lifetime = timedelta(minutes=30)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-temp-secret")

def load_data():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(current_dir, 'data.json')
        with open(data_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("data.json not found!")
        return {}

allTheData = load_data()

@app.route("/", methods=["GET"])
def start_game():
    session.permanent = True
    if not session.get("game_active") or session.get("game_complete"):
        player_found = False
        while not player_found:
            random_player = random.choice(list(allTheData.keys()))
            print(f"Selected Player: {random_player}")
            try:
                ppg = float(allTheData[random_player]['PPG'])
                rpg = float(allTheData[random_player]['RPG'])
                apg = float(allTheData[random_player]['APG'])
                player_found = True
            except:
                continue 

            session["game_active"] = True
            session["game_complete"] = False
            session["correct_player"] = random_player
            session["ppg"] = ppg
            session["apg"] = apg
            session["rpg"] = rpg
            session["division"] = defaultDivision(allTheData[random_player])
            height = allTheData[random_player]["HEIGHT"]
            session["inches"] = int(height[0]) * 12 + int(height[2])
            session["age"] = defaultAge(allTheData[random_player])
            session["guess_count"] = 0
            session["guesses"] = [{"name": "", "division": "", "height": "", "age": ""} for _ in range(8)]

    return render_template("index.html", ppg=session["ppg"], apg=session["apg"], rpg=session["rpg"], guesses=session["guesses"])

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

    # Check if the guess is correct
    if session["correct_player"] == guessedPlayer:
        session["game_complete"] = True  # Mark as complete
        return jsonify({
            "gameWon": True,
            "redirectTo": "/congrats",
            "guessCount": guess_count,
            "playerName": session["correct_player"],
            "imageUrl": image_url,
            "playerLink": player_link
        })
    
    else:
        # Check if max guesses reached
        if session["guess_count"] == 8:
            session["game_complete"] = True  # Mark as complete
            return jsonify({
                "gameOver": True,
                "redirectTo": "/failure", 
                "playerName": session["correct_player"],
                "imageUrl": image_url,
                "playerLink": player_link
            })
        
        # Process the guess and update session
        guesses[guess_count - 1]["name"] = guessedPlayer
        division = getDivision(allTheData[guessedPlayer])
        guesses[guess_count-1]['division'] = division[0]
        guesses[guess_count-1]['divColor'] = division[1]
        guesses[guess_count - 1]["height"] = getHeight(guessedPlayer)
        guesses[guess_count - 1]["ppg"] = allTheData[guessedPlayer]['PPG']
        guesses[guess_count - 1]["rpg"] = allTheData[guessedPlayer]['RPG']
        guesses[guess_count - 1]["apg"] = allTheData[guessedPlayer]['APG']
        guesses[guess_count - 1]["age"] = getAge(allTheData[guessedPlayer])
        
        # Update session with new guesses
        session["guesses"] = guesses
        
        # Return the guess result for AJAX update
        return jsonify({
            "gameWon": False,
            "gameOver": False,
            "guessResult": guesses[guess_count - 1]
        })

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').lower()
    def strip_accents(text):
        return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

    if query:
        norm_query = strip_accents(query)
        matches = [player for player in list(allTheData.keys()) if norm_query in strip_accents(player.lower())]
        return jsonify(matches)
    return jsonify([])

@app.route("/congrats")
def congrats():
    player_name = request.args.get("player_name")
    guess_count = request.args.get("guess_count", type=int)
    image_url = request.args.get("image_url")
    player_link = request.args.get("player_link")
    
    return render_template("congrats.html", 
                         player_name=player_name, 
                         guess_count=guess_count, 
                         image_url=image_url, 
                         player_link=player_link)

@app.route("/failure")
def failure():
    player_name = request.args.get("player_name")
    image_url = request.args.get("image_url")
    player_link = request.args.get("player_link")
    
    return render_template("failure.html", 
                         player_name=player_name, 
                         image_url=image_url, 
                         player_link=player_link)

@app.route("/reset")
def reset_game():
    # Clear game state to force new player selection
    session.pop("game_active", None)
    session.pop("game_complete", None)
    session.pop("correct_player", None)
    session.pop("guesses", None)
    session.pop("guess_count", None)
    return redirect("/")
            
def getDivision(guessedPlayerData):
    division = defaultDivision(guessedPlayerData)
    correct_division = session["division"]
    if division == correct_division:
        return [division, "#90EE90"]
    else:
        guessed_conf = None
        correct_conf = None
        for conference, divisions in conferenceBreakdown.items():
            if division in divisions:
                guessed_conf = conference
            if correct_division in divisions:
                correct_conf = conference
        if guessed_conf == correct_conf:
            return [division, "#FFFFC5"]
        return [division, "#FFCCCB"]

            
def getHeight(guessedPlayer):
    global allTheData
    height = allTheData[guessedPlayer]['HEIGHT']
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

def getAge(guessedPlayerData):
    age = defaultAge(guessedPlayerData)
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

def defaultDivision(playerDict):
    global allTheData
    for division, teamList in divisionBreakdown.items():
        if playerDict['TEAM'] in teamList:
            return division
        
def defaultAge(playerDict):
    bday_str = playerDict['BIRTHDAY']
    bday = datetime.strptime(bday_str, "%Y-%m-%d")  # Adjust format if needed
    age = (datetime.today() - bday).days // 365
    return age

if __name__ == "__main__":
    app.run()
