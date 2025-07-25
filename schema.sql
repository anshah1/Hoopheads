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
    ones INTEGER DEFAULT 0,    
    two INTEGER DEFAULT 0,    
    three INTEGER DEFAULT 0,    
    four INTEGER DEFAULT 0,    
    five INTEGER DEFAULT 0,    
    six INTEGER DEFAULT 0,    
    sevens INTEGER DEFAULT 0,    
    eights INTEGER DEFAULT 0,    
    fails INTEGER DEFAULT 0,    
    FOREIGN KEY (personUsername) REFERENCES users(username)
);
