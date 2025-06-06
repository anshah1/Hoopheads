import os
import random
import sys
import warnings
import psycopg2
from io import StringIO
from flask import Flask, redirect, render_template, session, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from data.dataStorage import divisions, players, allTheData, divisionBreakdown
warnings.simplefilter(action='ignore', category=FutureWarning)
from datetime import datetime, timedelta
from scraper.players import get_player_headshot, get_player_link
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
def get_db_connection():
    conn = psycopg2.connect(database="pgHoopheads", user="postgres",
                        password="", host="localhost", port="5432")
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
    print("This is guessed player: " + guessedPlayer)
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
        if "username" in session:
            for pair in matches:
                if session["guess_count"] == pair[0]:
                    guess_count_name = pair[1]
            
            db = get_db_connection()
            query = f"SELECT {guess_count_name} FROM stats WHERE personUsername = %s"
            current_in_that_guess = db['cursor'].execute(query, (session["username"],))
            print(f'Current in that guess is {current_in_that_guess}')
            if current_in_that_guess == None:
                current_in_that_guess = 1
            else: 
                current_in_that_guess = current_in_that_guess[0] + 1
            query = f"UPDATE stats SET {guess_count_name} = %s WHERE personUsername = %s"
            db['cursor'].execute(query, (current_in_that_guess, session["username"]))
            db['connection'].commit()

        return render_template("congrats.html", player_name=session["correct_player"], guess_count=guess_count, image_url=image_url, player_link = player_link)
    else:
        if session["guess_count"] == 8:
            if "username" in session:
                db = get_db_connection()
                current_fails = db['cursor'].execute("SELECT fails FROM stats WHERE personUsername = %s", (session["username"],))
                if current_fails == None:
                    current_fails = 1
                else:
                    current_fails = current_fails[0] + 1
                db['cursor'].execute("UPDATE stats SET fails = %s WHERE personUsername = %s", (current_fails, session["username"]))
                db['connection'].commit()
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
    if query:
        matches = [player for player in players if query in player.lower()]
        return jsonify(matches[:10])  
    return jsonify([]) 


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            error = "Username and password are required."
            return render_template("login.html", error=error)

        db = get_db_connection()
        db['cursor'].execute("SELECT hash FROM users WHERE username = %s", (username,))
        hash = db['cursor'].fetchone()
        print(f'Hash: {hash}')
        passwordCorrect = check_password_hash(hash[0], password)
        if hash is None or not passwordCorrect:
            error = "Invalid username and/or password."
            return render_template("login.html", error=error)

        session["username"] = username
        return redirect("/")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmation")

        if not username or not password or not confirm_password:
            error = "All fields are required."
            return render_template("register.html", error=error)

        if password != confirm_password:
            error = "Passwords don't match."
            return render_template("register.html", error=error)

        db = get_db_connection()
        db['cursor'].execute("SELECT username FROM users WHERE username = %s", (username,))
        existing_user = db['cursor'].fetchone()
        print(existing_user)
        if existing_user:
            error = "Username is already taken."
            return render_template("register.html", error=error)

        hashed_password = generate_password_hash(password)
        db['cursor'].execute(
            "INSERT INTO users (username, hash, streak, winCount, gamesPlayed) VALUES (%s, %s, 0, 0, 0)", 
            (username, hashed_password)
        )
        db['cursor'].execute(
            "INSERT INTO stats (personUsername) VALUES (%s)", (username,)
        )
        db['connection'].commit()
        session["username"] = username
        return redirect("/")

    return render_template("register.html")

@app.route("/stats")
def stats():
    db = get_db_connection()
    valid_keys = {'ones', 'two', 'three', 'four', 'five', 'six', 'sevens', 'eights', 'fails'}
    stats_to_add = {key: 0 for key in valid_keys}

    for key in stats_to_add:
        query = f"SELECT {key} FROM stats WHERE personusername = %s"
        db['cursor'].execute(query, (session["username"],))
        result = db['cursor'].fetchone()
        stats_to_add[key] = result[0] if result else 0

    return render_template("stats.html", ones = stats_to_add['ones'], twos = stats_to_add['two'], threes = stats_to_add['three'], fours = stats_to_add['four'], fives = stats_to_add['five'], sixes = stats_to_add['six'], sevens = stats_to_add['sevens'], eights = stats_to_add['eights'], fails = stats_to_add['fails'])

@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")

            
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
