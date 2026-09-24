# 📡 Competitor Radar

A lightweight, native Python automation that monitors a competitor's website (or any URL) for text changes, such as price drops or new features, and sends you a formatted Telegram alert showing exactly what was added or removed.

## ☁️ How to run this in the Cloud (Recommended)
Because this is a radar, you want it running every day automatically without having to leave your computer on. We use **GitHub Actions** to run this completely for free!

1. **Fork this repository** to your own GitHub account.
2. Go to your new repository's **Settings -> Secrets and variables -> Actions** and click *New repository secret*. Add these three:
   - `RADAR_BOT_TOKEN`: Your Telegram Bot Token (from @BotFather)
   - `RADAR_CHAT_ID`: Your personal Telegram Chat ID
   - `RADAR_TARGET_URLS`: The websites you want to monitor separated by a comma (e.g. `https://apple.com,https://google.com`)
3. Go to the **Actions** tab at the top of your repo and click **I understand my workflows, go ahead and enable them**.

That's it! GitHub will now check the website every morning at 8:00 AM UTC and ping your phone if anything changes!

---

## 💻 How to run locally (For developers)
If you just want to test the script on your own machine:
1. Copy `.env.example` to `.env` and add your variables.
2. Run `pip install -r requirements.txt`
3. Run `python radar.py`
