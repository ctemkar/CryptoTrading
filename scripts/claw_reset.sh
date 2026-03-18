# Kill any processes on 5000 or 5001
lsof -ti:5000,5001 | xargs kill -9 2>/dev/null

# Small delay to let the OS release the socket
sleep 1

# Start the app using the absolute .nvenv path
cd /Users/chetantemkar/.openclaw/workspace/app/
/Users/chetantemkar/.nvenv/bin/python3 app.py &

echo "Bot reset complete. Running on port 5000."
