CREATE DATABASE IF NOT EXISTS votebox;
USE votebox;

-- Users table
CREATE TABLE IF NOT EXISTS user (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL UNIQUE,
    password   VARCHAR(256) NOT NULL,
    is_admin   TINYINT      NOT NULL DEFAULT 0,
    created_at DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Elections table
CREATE TABLE IF NOT EXISTS election (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(100) NOT NULL,
    description TEXT         DEFAULT NULL,
    is_open     TINYINT      NOT NULL DEFAULT 1,
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Candidates table
CREATE TABLE IF NOT EXISTS candidate (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    election_id INT          NOT NULL,
    FOREIGN KEY (election_id) REFERENCES election(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Votes table (UNIQUE constraint prevents double voting)
CREATE TABLE IF NOT EXISTS vote (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT      NOT NULL,
    election_id  INT      NOT NULL,
    candidate_id INT      NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_election (user_id, election_id),
    FOREIGN KEY (user_id)      REFERENCES user(id),
    FOREIGN KEY (election_id)  REFERENCES election(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidate(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    admin_id   INT          NOT NULL,
    action     VARCHAR(50)  NOT NULL,
    target_id  INT          DEFAULT NULL,
    detail     VARCHAR(255) DEFAULT '',
    created_at DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES user(id)
) ENGINE=InnoDB;

-- Election summary view (candidate count + total votes)
CREATE OR REPLACE VIEW v_election_summary AS
SELECT
    e.id,
    e.title,
    e.description,
    e.is_open,
    e.created_at,
    COUNT(DISTINCT c.id) AS candidate_count,
    COUNT(DISTINCT v.id) AS total_votes
FROM election e
LEFT JOIN candidate c ON c.election_id = e.id
LEFT JOIN vote v ON v.election_id = e.id
GROUP BY e.id;

-- Candidate tallies view (vote counts per candidate)
CREATE OR REPLACE VIEW v_candidate_tallies AS
SELECT
    c.id AS candidate_id,
    c.name AS candidate_name,
    c.election_id,
    COUNT(v.id) AS vote_count
FROM candidate c
LEFT JOIN vote v ON v.candidate_id = c.id
GROUP BY c.id;

-- Seed: sample election
INSERT INTO election (title, description, is_open) VALUES (
    'Best Programming Language 2026',
    'Vote for your favorite programming language!',
    1
);

INSERT INTO candidate (name, election_id) VALUES ('Python', 1);
INSERT INTO candidate (name, election_id) VALUES ('JavaScript', 1);
INSERT INTO candidate (name, election_id) VALUES ('Rust', 1);
INSERT INTO candidate (name, election_id) VALUES ('Go', 1);
