import os
import psycopg2
from flask import Flask, request, send_file, render_template
import datetime
import requests

app = Flask(__name__)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# Initialize PostgreSQL database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracking (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            ip VARCHAR(50),
            country VARCHAR(100),
            region VARCHAR(100),
            city VARCHAR(100),
            user_agent TEXT,
            referrer TEXT,
            email TEXT
        )
    ''')
    conn.commit()
    cursor.close()
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
    email = request.args.get("email")
    ip = request.remote_addr
    user_agent = request.user_agent.string
    referrer = request.referrer or "No Referrer"
    timestamp = datetime.datetime.now()

    # Get geolocation data
    location = get_ip_info(ip)
    country, region, city = location["country"], location["region"], location["city"]

    # Store data in PostgreSQL
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tracking (timestamp, ip, country, region, city, user_agent, referrer, email) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (timestamp, ip, country, region, city, user_agent, referrer, email))
    
    conn.commit()
    cursor.close()
    conn.close()

    return send_file("static/pixel.png", mimetype="image/png")

# Fetch tracking data from the database
def get_tracking_data():
    """Retrieve the last 20 tracking entries from PostgreSQL"""
    conn = get_db_connection()
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
