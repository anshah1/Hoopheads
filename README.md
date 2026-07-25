# HoopHeads
Hoophead: Guess the NBA Player

Hoophead is an interactive basketball-themed game where users guess NBA players based on their 2025-2026 statistics. This project showcases my work in web development, database management, and game logic, offering a fun experience for basketball fans.

## Technologies Used
- Frontend: HTML, CSS, JavaScript (for real-time player search)
- Backend: Python (Flask), deployed on Vercel
-	Database: Supabase/Postgres (for storing user accounts and stats)
-	Data Scraping: basketball-reference, nba-api, and the Sportradar API for pulling player data
-	Session Management: Flask session to maintain game state

## Features
- Player Guessing Game: Players guess the NBA player based on points per game (PPG), rebounds per game (RPG), and assists per game (APG).
- User Accounts: Users can log in with Google to save their game stats.
- Player Stats: Users’ guessing statistics are tracked and displayed on their stats page - wins, streak, win %, guess distribution, and fails.
- Real NBA Data: The game uses real NBA player data for the 2025-2026 season.
- Responsive UI: The homepage includes an intuitive layout with user information and game instructions.

## Project Structure
**Top Banner**:
-	Includes hyperlinks to the important pages.
-	An info icon trigger modals with details about the game
-	If not logged in, users can log in with Google. If logged in, they can access stats or log out.
  
**Login**:
-	Users sign in through Google via Supabase Auth - no passwords to create or remember.
-	On first login a profile row is created in Supabase, keyed to the user's account, and their stats live there from then on.
  
**Stats Page**:
-	Displays user-specific statistics: cards for wins, current streak, and win percentage.
-	A bar chart shows the guess distribution - how many times the user won in each number of guesses (1 through 8).
-	Fails are listed underneath, and everything updates in Supabase each time a game finishes.
  
**NBA Player Data**:
-	Player data is scraped from basketball-reference, with bios and rosters cross-checked against nba-api and Sportradar.
-	A list of players (with at least 7 PPG in the 2025-2026 season) is stored in players.json, which the app loads once at startup for quick access during gameplay.
  
**Guessing Mechanics**:
-	When a user accesses the main page, a random player is selected from the pre-fetched player dictionary.
-	Players make guesses by typing into a search box, which suggests player names using JavaScript.
-	After selecting a player, their stats (division, height, age, PPG, RPG, APG) are compared to the correct player’s stats. The session stores the guesses.
-	Correct guesses lead to a congratulatory screen; after 8 incorrect guesses, the user is shown the correct player and a failure message.

## Installation

1.	Clone the repository:
```bash
  git clone https://github.com/anshah1/Hoopheads.git
```
2. Install the dependencies
```bash
pip install -r requirements.txt
```
3. Set up your environment variables
  Create a .env file with FLASK_SECRET_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SECRET_KEY, and SUPABASE_REDIRECT_URL.
4. Set up the Supabase project
  You need a profiles table with id, email, streak, guess_distribution, and fails columns, plus Google enabled as an auth provider.
5. Run the Application and open the link
```bash
flask run
```
6. Enjoy!!

## Acknowledgments

- Special thanks to basketball-reference-scraper by Vishaal Agartha and nba-api for making this possible

## Contact

Ansh Shah - [LinkedIn](https://www.linkedin.com/in/anshah18/)
