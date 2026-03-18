# Kill old instance
lsof -ti:5000 | xargs kill -9 2>/dev/null
# Start new instance using the virtual env
cd /Users/chetantemkar/.openclaw/workspace/app/
/Users/chetantemkar/.nvenv/bin/python3 app.py &
echo "[OK] Gateway restarted on port 5000"
