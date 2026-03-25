#!/bin/bash
cd /Users/aibot/clawd/polymarket-monitor
python3 continuous_monitor.py > monitor.log 2>&1 &
echo "Monitor started in background"
echo "Log file: monitor.log"
