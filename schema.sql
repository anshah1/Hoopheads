CREATE TABLE users (
 id SERIAL PRIMARY KEY,
 username TEXT NOT NULL UNIQUE,
 hash TEXT NOT NULL,
 streak NUMERIC NOT NULL,
 winCount NUMERIC NOT NULL,
 gamesPlayed NUMERIC NOT NULL
);

CREATE TABLE stats (
    personUsername TEXT NOT NULL,    
    guess_distribution INTEGER[] DEFAULT '{0,0,0,0,0,0,0,0}' 
    fails INTEGER DEFAULT 0,    
    FOREIGN KEY (personUsername) REFERENCES users(username)
);
