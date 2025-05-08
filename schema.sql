CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE stats (
    personUsername INTEGER,
    ones INTEGER DEFAULT 0,
    two INTEGER DEFAULT 0,
    three INTEGER DEFAULT 0,
    four INTEGER DEFAULT 0,
    five INTEGER DEFAULT 0,
    six INTEGER DEFAULT 0,
    sevens INTEGER DEFAULT 0,
    eights INTEGER DEFAULT 0,
    ails INTEGER DEFAULT 0,
    FOREIGN KEY (personUsername) REFERENCES users(ID)
);