import mysql.connector
import sys

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",       # <-- set your MySQL root password here
    "database": "votebox",
}

def promote(username):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return

    cur = conn.cursor(dictionary=True)
    
    # Check if user exists
    cur.execute("SELECT id FROM user WHERE username = %s", (username,))
    user = cur.fetchone()
    
    if not user:
        print(f"Error: User '{username}' not found. Please register this user in the app first.")
    else:
        cur.execute("UPDATE user SET is_admin = 1 WHERE username = %s", (username,))
        conn.commit()
        print(f"Success: '{username}' has been promoted to Admin.")
        print(f"You can now log in as '{username}' and access the Admin Panel to create polls.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python promote_admin.py <username>")
    else:
        promote(sys.argv[1])
