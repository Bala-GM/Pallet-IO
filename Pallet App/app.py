#!/usr/bin/env python3
import os
import sys
import sqlite3
from io import BytesIO
import webbrowser
import threading
import shutil
import datetime
import time
from flask import Flask, render_template, request, jsonify, send_file

# ========================
# Flask app
# ========================
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supersecretkey"

# ========================
# DB paths
# ========================
if getattr(sys, "frozen", False):
    # running as .exe
    BASE_DIR = os.path.join(os.environ["APPDATA"], "PalletIO")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOCAL_DB = os.path.join(BASE_DIR, "palletio.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# Ensure folders exist
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# ========================
# DB helper functions
# ========================
def init_db():
    if not os.path.exists(LOCAL_DB):
        db = sqlite3.connect(LOCAL_DB)
        db.execute("""
        CREATE TABLE pallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pallet_no TEXT,
            out_time TEXT,
            in_time TEXT
        )
        """)
        db.commit()
        db.close()
        print(f"✅ Database created at {LOCAL_DB}")

def get_db():
    db = sqlite3.connect(LOCAL_DB)
    db.row_factory = sqlite3.Row
    return db

# ========================
# Backup System
# ========================
def backup_db():
    if os.path.exists(LOCAL_DB):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        backup_name = os.path.join(BACKUP_DIR, f"palletio_{timestamp}.bak")
        shutil.copy2(LOCAL_DB, backup_name)
        print(f"✅ Backup created at {backup_name}")

def weekly_backup():
    while True:
        backup_db()
        time.sleep(7 * 24 * 60 * 60)  # 1 week

# ========================
# Routes
# ========================
@app.route("/")
def dashboard():
    db = get_db()
    pallets = db.execute("SELECT * FROM pallets ORDER BY id DESC").fetchall()
    db.close()
    return render_template("dashboard.html", pallets=pallets)

@app.route("/scan", methods=["POST"])
def scan():
    data = request.get_json()
    pallet_no = data.get("pallet_no", "").strip()
    if not pallet_no:
        return jsonify({"status": "error", "message": "Empty pallet number"})

    db = get_db()
    last_record = db.execute(
        "SELECT * FROM pallets WHERE pallet_no = ? ORDER BY id DESC LIMIT 1",
        (pallet_no,)
    ).fetchone()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if last_record is None or last_record["in_time"] is not None:
        db.execute(
            "INSERT INTO pallets (pallet_no, out_time, in_time) VALUES (?, ?, ?)",
            (pallet_no, now, None)
        )
    else:
        db.execute(
            "UPDATE pallets SET in_time = ? WHERE id = ?",
            (now, last_record["id"])
        )

    db.commit()
    pallets = db.execute("SELECT * FROM pallets ORDER BY id DESC").fetchall()
    db.close()

    pallets_list = [dict(p) for p in pallets]
    return jsonify({"status": "success", "pallets": pallets_list})

@app.route("/download")
def download_report():
    db = get_db()
    pallets = db.execute("SELECT * FROM pallets ORDER BY id DESC").fetchall()
    db.close()

    output = "ID,Pallet No,Out Time,In Time\n"
    for p in pallets:
        output += f'{p["id"]},{p["pallet_no"]},{p["out_time"]},{p["in_time"] or ""}\n'

    bytes_io = BytesIO()
    bytes_io.write(output.encode("utf-8"))
    bytes_io.seek(0)

    return send_file(
        bytes_io,
        mimetype="text/csv",
        as_attachment=True,
        download_name="pallets_report.csv"
    )

# ========================
# Main
# ========================
if __name__ == "__main__":
    init_db()

    # Start weekly backup thread
    threading.Thread(target=weekly_backup, daemon=True).start()

    # Auto open browser after 1 sec
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5006")).start()

    # Run Flask
    app.run(debug=False, port=5006)

#pyinstaller --onefile --name Pallet_Scanning_Dashboard --add-data "static;static" --add-data "templates;templates" --hidden-import flask --noconsole --icon=favicon.ico app.py