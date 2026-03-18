#!/bin/bash

# Crypto Trading System Backup Script
# Runs hourly to backup trading files to CryptoTrading repository

BACKUP_DIR="/tmp/crypto-backup-$(date +%Y%m%d_%H%M%S)"
REPO_DIR="/tmp/crypto-backup"
LOG_FILE="/Users/chetantemkar/.openclaw/workspace/app/backup_log.txt"

echo "=== Crypto Trading Backup $(date) ===" >> "$LOG_FILE"

# Create backup directory
mkdir -p "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR/src" "$BACKUP_DIR/templates" "$BACKUP_DIR/static" "$BACKUP_DIR/scripts"

# Copy essential trading files
cd /Users/chetantemkar/.openclaw/workspace/app

# Source code
cp -f app.py gateway.py trading_server.py check_trading_v2.py analyze_position.py market_analysis_current.py "$BACKUP_DIR/src/" 2>/dev/null || true

# Templates
cp -rf templates/* "$BACKUP_DIR/templates/" 2>/dev/null || true

# Static files
cp -rf static/* "$BACKUP_DIR/static/" 2>/dev/null || true

# Scripts and documentation
cp -f *.sh *.md requirements.txt "$BACKUP_DIR/scripts/" 2>/dev/null || true
cp -f HEARTBEAT.md MEMORY.md "$BACKUP_DIR/scripts/" 2>/dev/null || true

# Check if repository exists, clone if not
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "Cloning CryptoTrading repository..." >> "$LOG_FILE"
    rm -rf "$REPO_DIR"
    git clone https://github.com/ctemkar/CryptoTrading.git "$REPO_DIR"
fi

# Update repository with latest files
cd "$REPO_DIR"
git pull origin main

# Copy new files
rm -rf "$REPO_DIR/src" "$REPO_DIR/templates" "$REPO_DIR/static" "$REPO_DIR/scripts"
cp -r "$BACKUP_DIR/src" "$REPO_DIR/"
cp -r "$BACKUP_DIR/templates" "$REPO_DIR/"
cp -r "$BACKUP_DIR/static" "$REPO_DIR/"
cp -r "$BACKUP_DIR/scripts" "$REPO_DIR/"

# Commit and push
git add .
if git diff --cached --quiet; then
    echo "No changes to commit" >> "$LOG_FILE"
else
    git commit -m "Hourly backup: $(date '+%Y-%m-%d %H:%M:%S')"
    git push origin main
    echo "Backup completed successfully" >> "$LOG_FILE"
fi

# Cleanup
rm -rf "$BACKUP_DIR"

echo "Backup process completed at $(date)" >> "$LOG_FILE"