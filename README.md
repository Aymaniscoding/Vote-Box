# VoteBox - Online Voting System

VoteBox is a secure web-based voting platform built using Flask, MySQL, HTML, CSS, and JavaScript. It allows users to register, log in, participate in elections, cast votes, and view election results while providing administrators with tools to manage elections and monitor system activity.

⸻

#Features

#User Features

* User Registration & Login
* Secure Password Hashing
* Session-Based Authentication
* Browse Available Elections
* Cast Votes
* One Vote Per Election Enforcement
* View Election Results

#Admin Features

* Create and Manage Elections
* Add Candidates
* Open/Close Elections
* Promote Users to Admin
* Audit Log Tracking
* Election Statistics Dashboard

#Security Features

* CSRF Protection
* Password Hashing using Werkzeug
* Session Management
* Input Validation
* Duplicate Vote Prevention
* Role-Based Access Control

⸻

#Tech Stack

#Backend

* Python
* Flask
* MySQL
* Werkzeug Security

Frontend

* HTML
* CSS
* JavaScript

Database

* MySQL

⸻

#Project Structure

votebox/
│
├── app.py                  # Main Flask application
├── schema.sql              # Database schema and sample data
├── setup_db.py             # Database setup script
├── promote_admin.py        # Promote user to admin
├── requirements.txt        # Project dependencies
├── run.sh                  # Linux/Mac startup script
├── run.bat                 # Windows startup script
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
└── voting.db


#Security Measures

* Password Hashing
* CSRF Token Validation
* Secure Session Cookies
* Input Length Validation
* Admin Authorization Checks
* Duplicate Voting Prevention

⸻

Sample Election

The database is seeded with a sample election:

Best Programming Language 2026

Candidates:

* Python
* JavaScript
* Rust
* Go
