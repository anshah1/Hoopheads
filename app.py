import os
import random
import sqlite3
import sys
import warnings
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
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = os.urandom(24) 

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
    conn = sqlite3.connect("hoophead.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/", methods=["GET"])
def start_game():
    session.permanent = True
    playerFound = False
    while not playerFound:
        randomPlayer = random.choice(allTheData)
        try:
            ppg = float(randomPlayer['PPG'])
            rpg = float(randomPlayer['RPG'])
            apg = float(randomPlayer['APG'])
            playerFound = True
        except:
            continue  # skip malformed player

    session["correct_player"] = randomPlayer["NAME"]
    session["ppg"] = ppg
    session["apg"] = apg
    session["rpg"] = rpg
    session["division"] = defaultDivision(randomPlayer)
    height = randomPlayer["HEIGHT"]
    session["inches"] = int(height[0]) * 12 + int(height[2])
    session["age"] = defaultAge(randomPlayer['NAME'])
    session["guessCount"] = 0
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
    guessCount = session.get("guessCount", 0) + 1
    session["guessCount"] = guessCount

    imageURL = get_player_headshot(session["correct_player"])
    print(f"Player Image URL: {imageURL}")
    if imageURL is None:
        imageURL = "https://www.logodesignlove.com/images/classic/nba-logo.jpg"

    playerLink = get_player_link(session["correct_player"])
    print(f"Player Link: {playerLink}")

    if session["correct_player"] == guessedPlayer:
        if "username" in session:
            for pair in matches:
                if session["guessCount"] == pair[0]:
                    guessCountName = pair[1]
            
            db = get_db_connection()
            query = f"SELECT {guessCountName} FROM stats WHERE personUsername = ?"
            currentInThatGuess = db.execute(query, (session["username"],)).fetchone()
            currentInThatGuess = currentInThatGuess[0] + 1
            query = f"UPDATE stats SET {guessCountName} = ? WHERE personUsername = ?"
            db.execute(query, (currentInThatGuess, session["username"]))
            db.commit()

        return render_template("congrats.html", player_name=session["correct_player"], guess_count=guessCount, imageURL=imageURL, playerLink = playerLink)
    else:
        if session["guessCount"] == 8:
            if "username" in session:
                db = get_db_connection()
                currentFails = db.execute("SELECT fails FROM stats WHERE personUsername = ?", (session["username"],)).fetchone()
                currentFails = currentFails[0] + 1
                db.execute("UPDATE stats SET fails = ? WHERE personUsername = ?", (currentFails, session["username"]))
                db.commit()
            return render_template("failure.html", player_name = session["correct_player"], imageURL=imageURL, playerLink = playerLink)
        guesses[guessCount - 1]["name"] = guessedPlayer
        guesses[guessCount-1]['division'] = getDivision(guessedPlayer)[0]
        guesses[guessCount-1]['divColor'] = getDivision(guessedPlayer)[1]
        guesses[guessCount - 1]["height"] = getHeight(guessedPlayer)
        guesses[guessCount - 1]["ppg"] = getPoints(guessedPlayer)
        guesses[guessCount - 1]["rpg"] = getRebounds(guessedPlayer)
        guesses[guessCount - 1]["apg"] = getAssists(guessedPlayer)
        guesses[guessCount - 1]["age"] = getAge(guessedPlayer)
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
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user is None or not check_password_hash(user["hash"], password):
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
        confirmPassword = request.form.get("confirmation")

        if not username or not password or not confirmPassword:
            error = "All fields are required."
            return render_template("register.html", error=error)

        if password != confirmPassword:
            error = "Passwords don't match."
            return render_template("register.html", error=error)

        db = get_db_connection()
        existing_user = db.execute("SELECT username FROM users WHERE username = ?", (username,)).fetchone()
        
        if existing_user:
            error = "Username is already taken."
            return render_template("register.html", error=error)

        hashedPassword = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (username, hash, streak, winCount, gamesPlayed) VALUES (?, ?, 0, 0, 0)", 
            (username, hashedPassword)
        )
        db.execute(
            "INSERT INTO stats (personUsername) VALUES (?)", (username,)
        )
        db.commit()
        session["username"] = username
        return redirect("/")

    return render_template("register.html")

@app.route("/stats")
def stats():
    db = get_db_connection()
    ones = db.execute("SELECT ones FROM stats WHERE personUsername = ?", (session["username"],)).fetchone()
    two = db.execute("SELECT two FROM stats WHERE personUsername = ?", (session["username"],)).fetchone()
    three = db.execute("SELECT three FROM stats WHERE personUsername = ?", (session["username"],)).fetchone()
    four = db.execute("SELECT four FROM stats WHERE personUsername = ?", (session["username"],)).fetchone()
    five = db.execute("SELECT five FROM stats WHERE personUsername = ?", (session["username"],)).fetchone()
    six = db.execute("SELECT six FROM stats WHERE personUsername = ?", (session["username"],)).fetchone()
    sevens = db.execute("SELECT sevens FROM stats WHERE personUsername = ?", (session["username"],)).fetchone()
    eights = db.execute("SELECT eights FROM stats WHERE personUsername = ?", (session["username"],)).fetchone()
    fails = db.execute("SELECT fails FROM stats WHERE personUsername = ?", (session["username"],)).fetchone()
    
    ones_value = ones["ones"] if ones else 0
    two_value = two["two"] if two else 0
    three_value = three["three"] if three else 0
    four_value = four["four"] if four else 0
    five_value = five["five"] if five else 0
    six_value = six["six"] if six else 0
    sevens_value = sevens["sevens"] if sevens else 0
    eights_value = eights["eights"] if eights else 0
    fails_value = fails["fails"] if fails else 0

    return render_template("stats.html", 
                           ones=ones_value, 
                           two=two_value, 
                           three=three_value, 
                           four=four_value, 
                           five=five_value, 
                           six=six_value, 
                           sevens=sevens_value, 
                           eights=eights_value, 
                           fails=fails_value)

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