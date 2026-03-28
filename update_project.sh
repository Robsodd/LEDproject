#!/bin/bash

# Navigate to the project folder
cd /home/robsodd/LEDproject

echo "--- 🔄 Updating LEDProject ---"

# 1. Pull the latest code from GitHub
git pull origin main

# 2. Re-install requirements (in case of new libraries)
source venv/bin/activate
pip install -r requirements.txt

# 3. Restart the system service
echo "--- 🔌 Restarting Service ---"
sudo systemctl restart rainbow.service

echo "--- ✅ Update Complete! ---"
