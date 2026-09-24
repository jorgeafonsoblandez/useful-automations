import os
import sys
import difflib
import requests
import hashlib
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TARGET_URLS = os.getenv("TARGET_URLS", os.getenv("TARGET_URL")) # Backwards compatible

def get_snapshot_filename(url: str) -> str:
    """Generates a safe, unique filename for each URL's snapshot."""
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    return f"snapshot_{url_hash}.txt"

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
    
    soup = BeautifulSoup(response.text, "html.parser")
    for script in soup(["script", "style", "noscript", "meta", "header", "footer"]):
        script.decompose()
        
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def process_url(url: str):
    try:
        current_text = fetch_page_text(url)
    except Exception as e:
        print(f"❌ Failed to process {url}: {e}")
        return

    state_file = get_snapshot_filename(url)

    # Check if we have a previous snapshot to compare against
    if not os.path.exists(state_file):
        print(f"📝 No previous snapshot found for {url}. Saving initial state...")
        with open(state_file, "w", encoding="utf-8") as f:
            f.write(current_text)
        print("✅ Initial state saved!")
        return

    # Read the old snapshot
    with open(state_file, "r", encoding="utf-8") as f:
        previous_text = f.read()

    if current_text == previous_text:
        print(f"💤 No changes detected on {url}.")
        return

    # If it differs, let's find out what changed!
    print(f"🚨 Changes detected on {url}! Generating report...")
    
    # We create a simple diff summary with 1 line of context (which usually catches the product name!)
    diff = difflib.unified_diff(
        previous_text.splitlines(),
        current_text.splitlines(),
        lineterm="",
        n=1  # 1 line of context
    )
    
    diff_lines = list(diff)[2:]  # Skip the file header lines
    raw_added = [line[1:].strip() for line in diff_lines if line.startswith('+') and line.strip() != '+']
    raw_removed = [line[1:].strip() for line in diff_lines if line.startswith('-') and line.strip() != '-']
    
    # Filter out lines that just moved around in the HTML (they appear in both lists)
    added_set = set(raw_added)
    removed_set = set(raw_removed)
    
    added = [line for line in raw_added if line not in removed_set]
    removed = [line for line in raw_removed if line not in added_set]
    
    # If after filtering there are no actual text changes, skip the alert!
    if not added and not removed:
        print(f"💤 Only layout/movement changes detected on {url}. Skipping alert.")
        # We still save the state below so we have the latest HTML structure
    else:
        # Format the Telegram alert
        message = f"🚨 <b>Competitor Radar Alert</b> 🚨\n\nChanges detected on: <a href='{url}'>{url}</a>\n"
        
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
    with open(state_file, "w", encoding="utf-8") as f:
        f.write(current_text)
    print(f"✅ State updated for {url}.")

def main():
    if not TARGET_URLS:
        print("❌ Please set TARGET_URLS in your .env file (comma-separated if multiple).")
        sys.exit(1)
        
    urls = [u.strip() for u in TARGET_URLS.split(",") if u.strip()]
    print(f"🚀 Starting Radar for {len(urls)} target(s)...")
    
    for url in urls:
        process_url(url)
        print("-" * 30)

if __name__ == "__main__":
    main()
