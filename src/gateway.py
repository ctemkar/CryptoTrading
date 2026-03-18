from flask import Flask, redirect
import os
BASE_DIR = "/Users/chetantemkar/.openclaw/workspace/app"
app = Flask(__name__)
@app.route("/")
def index():
    try:
        with open(os.path.join(BASE_DIR, ".active_port"), "r") as f:
            port = f.read().strip()
        return redirect(f"http://127.0.0.1:{port}")
    except:
        return "Dashboard not running. Please start the bot."
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
