# HoopHeads
Hoophead: Guess the NBA Player

Hoophead is an interactive basketball-themed game where users guess NBA players based on their 2024-2025 statistics. This project showcases my work in web development, database management, and game logic, offering a fun experience for basketball fans.

## Technologies Used
- Frontend: HTML, CSS, JavaScript (for real-time player search)
- Backend: Python (Flask)
-	Database: SQLite3 (for storing user accounts and stats)
-	Data Scraping: basketball-reference-scraper for pulling player data
-	Session Management: Flask session to maintain game state

## Features
- Player Guessing Game: Players guess the NBA player based on points per game (PPG), rebounds per game (RPG), and assists per game (APG).
- User Accounts: Users can register and log in to save their game stats.
- Player Stats: Users’ guessing statistics are tracked and displayed in their account profile.
- Real NBA Data: The game uses real NBA player data for the 2023-2024 season.
- Responsive UI: The homepage includes an intuitive layout with user information and game instructions.

## Project Structure
**Top Banner**:
-	Includes hyperlinks to the important pages.
-	An info icon trigger modals with details about the game
-	If not logged in, users can register or log in. If logged in, they can access stats or log out.
  
**Register and Login**:
-	Users can create an account with a unique username and a matching password confirmation.
-	Users can log in with their credentials, and the site verifies the username and hashed password via SQLite3.
  
**Stats Page**:
-	Displays user-specific statistics in a 2-row, 9-column table.
-	Top row: Number of guesses + failures.
-	Bottom row: Count of how many times users scored each number of guesses.
-	Stats are stored and updated in the SQLite3 database each time a guess is made.
  
**NBA Player Data**:
-	Player data is sourced from basketball-reference using the basketball-reference-scraper library.
-	A list of players (with at least 7 PPG in the 2024 season) is fetched and stored in a dictionary, which is used for quick access during gameplay.
  
**Guessing Mechanics**:
-	When a user accesses the main page, a random player is selected from the pre-fetched player dictionary.
-	Players make guesses by typing into a search box, which suggests player names using JavaScript.
-	After selecting a player, their stats (division, height, PPG, RPG, APG) are compared to the correct player’s stats. The session stores the guesses.
-	Correct guesses lead to a congratulatory screen; after 8 incorrect guesses, the user is shown the correct player and a failure message.

## Installation

1.	Clone the repository:
```bash
  git clone https://github.com/yourusername/hoophead-nba-game.git
```
2. Install Flask
```bash
pip install Flask
```
3. Install Flask Session
```bash
pip install Flask-Session```
```
4. Set up the SQLite3 Database
  The database file hoophead.db is required for user accounts and stats storage.
  Use the provided schema in schema.sql to create the necessary tables.
5. Run the Application and open the link
```bash
flask run
```
6. Enjoy!!

## Acknowledgments

- Special thanks to basketball-reference-scraper by Vishaal Agartha and nba-api for making this possible

## Contact

Ansh Shah - [LinkedIn](https://www.linkedin.com/in/anshah18/)




Gitingore



venv/
__pycache__/
*.py[cod]
*.db
*.log

