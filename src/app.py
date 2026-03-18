from flask import Flask, jsonify, render_template
import os, json, psutil, subprocess
from datetime import datetime
app = Flask(__name__, template_folder='templates', static_folder='static')
BASE_DIR = "/Users/chetantemkar/.openclaw/workspace/app"

def get_status():
    try:
        for p in psutil.process_iter(['cmdline']):
            if "crypto_trading_llm_live.py" in " ".join(p.info.get('cmdline', [])): return "RUNNING"
        return "STOPPED"
    except: return "STOPPED"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/status/all')
def status_data():
    return jsonify({"status": get_status(), "trades": [], "timestamp": datetime.now().strftime("%H:%M:%S")})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5080)
