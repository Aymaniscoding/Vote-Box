import mysql.connector
import sys
import getpass
from werkzeug.security import generate_password_hash

# ── MySQL connection config (same as app.py) ──
DB_NAME = "votebox"

def get_mysql_password():
    """Get MySQL password from command line arg, env var, or prompt."""
    if len(sys.argv) >= 2:
        return sys.argv[1]
    import os
    if os.environ.get("DB_PASSWORD"):
        return os.environ["DB_PASSWORD"]
    return getpass.getpass("Enter MySQL root password (press Enter if none): ")

def setup():
    mysql_password = get_mysql_password()
    
    DB_CONFIG = {
        "host":     "localhost",
        "user":     "root",
        "password": mysql_password,
    }
    
    # Connect without specifying a database first
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        print("Make sure MySQL is running and your password is correct.")
        print("Usage: python setup_db.py [mysql_root_password]")
        return
    cur = conn.cursor()

    # Drop and recreate the database
    print("Dropping existing database (if any)...")
    cur.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
    cur.execute(f"CREATE DATABASE {DB_NAME}")
    cur.execute(f"USE {DB_NAME}")
    print(f"Database '{DB_NAME}' created.")

    # Read and execute schema file
    with open("schema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Execute multi-statement SQL
    for result in cur.execute(schema_sql, multi=True):
        pass  # consume results

    conn.commit()

    # Create default admin user with hashed password
    hashed = generate_password_hash("admin123")
    cur.execute(
        "INSERT INTO user (username, password, is_admin) VALUES (%s, %s, 1)",
        ("admin", hashed)
    )
    conn.commit()

    cur.close()
    conn.close()

    print("Database initialized successfully!")
    print("Default admin account created:")
    print("   Username: admin")
    print("   Password: admin123")
    print("   (Change this password after first login!)")

if __name__ == "__main__":
    setup()
