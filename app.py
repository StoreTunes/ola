from flask import Flask, request, send_file, render_template
import datetime
import sqlite3
import requests
import os

app = Flask(__name__)

DB_FILE = "tracking_data.db"

# Initialize the database
def init_db():
    """Create the database and table if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        ip TEXT,
                        country TEXT,
                        region TEXT,
                        city TEXT,
                        user_agent TEXT,
                        referrer TEXT
                    )''')
    conn.commit()
    conn.close()

init_db()

# Fetch IP Geolocation Data
def get_ip_info(ip):
    """Fetch geolocation data from IPinfo.io"""
    API_URL = f"https://ipinfo.io/{ip}/json?token=d606cdfca90d93"
    try:
        response = requests.get(API_URL, timeout=5)
        data = response.json()
        return {
            "country": data.get("country", "Unknown"),
            "region": data.get("region", "Unknown"),
            "city": data.get("city", "Unknown")
        }
    except Exception:
        return {"country": "Unknown", "region": "Unknown", "city": "Unknown"}

@app.route('/track_pixel')
def track():
    """Track user visit and serve a 1x1 transparent pixel"""
    ip = request.remote_addr
    user_agent = request.user_agent.string
    referrer = request.referrer or "No Referrer"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get geolocation
    location = get_ip_info(ip)
    country, region, city = location["country"], location["region"], location["city"]

    # Store tracking data in database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO tracking (timestamp, ip, country, region, city, user_agent, referrer) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (timestamp, ip, country, region, city, user_agent, referrer))
    conn.commit()
    conn.close()

    # Return the tracking pixel
    return send_file("static/pixel.png", mimetype="image/png")

# Fetch tracking data from the database
def get_tracking_data():
    """Retrieve the last 20 tracking entries"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, ip, country, region, city, user_agent, referrer FROM tracking ORDER BY id DESC LIMIT 20")
    data = cursor.fetchall()
    conn.close()
    return [{"timestamp": row[0], "ip": row[1], "country": row[2], "region": row[3], "city": row[4], "user_agent": row[5], "referrer": row[6]} for row in data]

@app.route("/")
def index():
    """Render the tracking dashboard"""
    tracking_data = get_tracking_data()
    return render_template("index.html", tracking_data=tracking_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

