import os
import re
import time
import json
import requests
from flask import Flask, request, Response, jsonify
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- Config ---
TARGET_BASE = os.getenv("TARGET_BASE", "https://pakistandatabase.com")
TARGET_PATH = os.getenv("TARGET_PATH", "/databases/sim.php")
COPYRIGHT_HANDLE = os.getenv("COPYRIGHT_HANDLE", "@never_delete")

# --- Helpers ---
def classify_query(value: str):
    v = str(value).strip()
    if re.fullmatch(r"92\d{9,10}", v):
        return "mobile", v
    if re.fullmatch(r"\d{13}", v):
        return "cnic", v
    raise ValueError("Invalid format. Use 923xxxxxxxxx or 13-digit CNIC.")

def fetch_data(query_value):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": TARGET_BASE,
        "Referer": f"{TARGET_BASE}/"
    }
    try:
        resp = requests.post(
            f"{TARGET_BASE.rstrip('/')}{TARGET_PATH}",
            data={"search_query": query_value},
            headers=headers,
            timeout=15
        )
        resp.raise_for_status()
        return resp.text
    except:
        return None

def parse_results(html):
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table: return []
    
    rows = []
    for tr in table.find_all("tr")[1:]: # Skip header
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cols) >= 4:
            rows.append({
                "number": cols[0],
                "name": cols[1],
                "cnic": cols[2],
                "address": cols[3]
            })
    return rows

# --- Routes ---
@app.route('/')
def index():
    return jsonify({
        "status": "Active",
        "endpoint": "/api/lookup?q=QUERY",
        "developer": COPYRIGHT_HANDLE
    })

@app.route('/api/lookup', methods=['GET'])
def lookup():
    query = request.args.get('q') or request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    
    try:
        q_type, q_val = classify_query(query)
        html = fetch_data(q_val)
        results = parse_results(html)
        
        return Response(
            json.dumps({
                "success": True,
                "type": q_type,
                "count": len(results),
                "results": results,
                "credit": f"👉🏻 {COPYRIGHT_HANDLE}"
            }, indent=4, ensure_ascii=False),
            mimetype="application/json"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Vercel-এর জন্য এই অবজেক্টটি প্রয়োজন
app = app