# 📡 Competitor Radar

A lightweight, native Python automation that monitors a competitor's website (or any URL) for text changes, such as price drops or new features, and sends you a formatted Telegram alert showing exactly what was added or removed.

## Setup
1. Copy `.env.example` to `.env` and add your `TARGET_URL` and Telegram credentials.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the script: `python radar.py`

*(Note: The first run saves the baseline snapshot. Subsequent runs will compare against it and alert you if changes occurred).*
