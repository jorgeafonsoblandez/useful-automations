import os
import sys
import difflib
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TARGET_URL = os.getenv("TARGET_URL")
STATE_FILE = "last_snapshot.txt"

def send_telegram_message(message: str):
    """Sends a message via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing. Printing to console instead:")
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Failed to send Telegram message: {response.text}")
    else:
        print("✅ Alert sent to Telegram!")

def fetch_page_text(url: str) -> str:
    """Uses requests and BeautifulSoup to extract visible text."""
    print(f"🔍 Scraping {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    
    # Parse the HTML and extract text
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Remove script and style elements
    for script in soup(["script", "style", "noscript", "meta", "header", "footer"]):
        script.decompose()
        
    # Get text and collapse whitespace
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def main():
    if not TARGET_URL:
        print("❌ Please set TARGET_URL in your .env file.")
        sys.exit(1)

    try:
        current_text = fetch_page_text(TARGET_URL)
    except Exception as e:
        print(e)
        sys.exit(1)

    # Check if we have a previous snapshot to compare against
    if not os.path.exists(STATE_FILE):
        print("📝 No previous snapshot found. Saving initial state...")
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(current_text)
        print("✅ Initial state saved! The next time this runs, it will check for changes.")
        return

    # Read the old snapshot
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        previous_text = f.read()

    if current_text == previous_text:
        print("💤 No changes detected on the page.")
        return

    # If it differs, let's find out what changed!
    print("🚨 Changes detected! Generating report...")
    
    # We create a simple diff summary (just checking line additions/removals)
    diff = difflib.unified_diff(
        previous_text.splitlines(),
        current_text.splitlines(),
        lineterm="",
        n=0  # 0 lines of context to keep it short
    )
    
    diff_lines = list(diff)[2:]  # Skip the file header lines
    added = [line[1:].strip() for line in diff_lines if line.startswith('+') and line.strip() != '+']
    removed = [line[1:].strip() for line in diff_lines if line.startswith('-') and line.strip() != '-']
    
    # Format the Telegram alert
    message = f"🚨 <b>Competitor Radar Alert</b> 🚨\n\nChanges detected on: <a href='{TARGET_URL}'>{TARGET_URL}</a>\n"
    
    if added:
        message += "\n🟢 <b>Added Content:</b>\n"
        for line in added[:5]:  # limit to top 5 changes so the message isn't massive
            message += f"• {line[:50]}...\n"
            
    if removed:
        message += "\n🔴 <b>Removed Content:</b>\n"
        for line in removed[:5]:
            message += f"• {line[:50]}...\n"
            
    message += "\n<i>Go check the page to see the full details!</i>"
    
    send_telegram_message(message)

    # Save the new state so we don't alert again tomorrow unless it changes again
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(current_text)
    print("✅ State updated.")

if __name__ == "__main__":
    main()
