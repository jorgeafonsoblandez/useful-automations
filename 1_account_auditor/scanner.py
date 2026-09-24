import imaplib
import email
import os
import re
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
APP_PASSWORD = os.getenv("APP_PASSWORD")

def extract_email_address(from_header: str) -> str:
    """Extracts just the email address from a 'From' header."""
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1).lower()
    return from_header.strip().lower()

def extract_domain(email_address: str) -> str:
    """Extracts the domain from an email address."""
    if "@" in email_address:
        return email_address.split("@")[1]
    return email_address

def scan_inbox():
    if not EMAIL_ACCOUNT or not APP_PASSWORD:
        print("❌ Please set EMAIL_ACCOUNT and APP_PASSWORD in your .env file.")
        return

    print(f"🔒 Connecting securely to {IMAP_SERVER}...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
    except Exception as e:
        print(f"❌ Login failed: {e}")
        print("Make sure you are using an 'App Password', not your main account password!")
        return
        
    print("✅ Logged in successfully. Selecting inbox...")
    mail.select("inbox")
    
    # Search for emails that likely represent accounts or subscriptions
    # 'BODY "unsubscribe"' is a great proxy for automated systems, mailing lists, and corporate accounts
    print("🔍 Scanning inbox for subscriptions and accounts (this might take a moment)...")
    status, messages = mail.search(None, 'BODY "unsubscribe"')
    
    if status != "OK":
        print("No messages found!")
        return
        
    email_ids = messages[0].split()
    print(f"📥 Found {len(email_ids)} emails associated with subscriptions or accounts.")
    
    senders = Counter()
    domains = Counter()
    
    # Process up to the last 3000 emails to get a more comprehensive view
    limit = 3000
    process_ids = email_ids[-limit:]
    
    print(f"⚙️ Extracting data from the {len(process_ids)} most recent matches...")
    
    # Process in batches of 200 to reduce network round-trips
    # This turns 1000 slow requests into 5 lightning-fast requests!
    chunk_size = 200
    for i in range(0, len(process_ids), chunk_size):
        chunk = process_ids[i:i + chunk_size]
        id_list = b",".join(chunk)
        
        res, msg_data = mail.fetch(id_list, '(BODY[HEADER.FIELDS (FROM)])')
        if res != "OK":
            continue
            
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                from_header = msg.get("From")
                if from_header:
                    clean_email = extract_email_address(from_header)
                    domain = extract_domain(clean_email)
                    
                    senders[clean_email] += 1
                    domains[domain] += 1
                    
    mail.logout()
    
    print("\n" + "="*50)
    print("📊 ACCOUNT & SUBSCRIPTION AUDIT REPORT")
    print("="*50)
    
    print("\n🏢 TOP COMPANIES/DOMAINS WITH YOUR DATA:")
    for domain, count in domains.most_common(20):
        print(f"  - {domain} ({count} emails)")
        
    print("\n📬 TOP SPECIFIC SENDERS:")
    for sender, count in senders.most_common(10):
        print(f"  - {sender}")

    print("\n" + "="*50)
    print("💡 Next Step: Generating AI Action Plan...")
    
    # Pass top 20 domains now
    top_domains = domains.most_common(20)
    generate_action_plan(top_domains, len(process_ids))

def generate_action_plan(domains_list, scanned_count):
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("\n⚠️ GEMINI_API_KEY not found in .env! Skipping AI Action Plan generation.")
        print("To get a free key, visit: https://aistudio.google.com/app/apikey")
        return
        
    print("🧠 Asking AI to find direct Delete/Unsubscribe links for you...")
    
    from google import genai
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = (
            "I am auditing my digital footprint. Here are the top domains sending me emails. "
            "For each company, provide the direct URL to delete my account, and the URL to unsubscribe. "
            "IMPORTANT: If there are multiple subdomains for the same company (e.g. 'order.temu.com' and 'orders.temu.com'), "
            "MERGE them into a single row for that company. Do not list duplicates.\n\n"
            "Format the output as a beautiful, simple, standalone HTML webpage. "
            "Use a modern, clean font, put the data in a nice HTML table. "
            f"At the very top of the webpage, include this exact disclaimer in italics: "
            f"'Disclaimer: This report is based on a scan of the {scanned_count} most recent promotional emails in your inbox.'\n"
            "Make sure the URLs are actual clickable HTML <a> links. "
            "Do not include markdown code blocks like ```html, just output the raw HTML code directly.\n\nDomains:\n"
        )
        for domain, count in domains_list:
            prompt += f"- {domain}\n"
            
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        
        # Clean up any accidental markdown formatting the AI might still add
        html_content = response.text.replace("```html", "").replace("```", "").strip()
        
        with open("audit_report.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print("✅ Action plan generated and saved to 'audit_report.html'!")
        print("Simply double-click 'audit_report.html' to open it in your web browser and start clicking the links!")
        
    except Exception as e:
        print(f"❌ AI Generation failed: {e}")

if __name__ == "__main__":
    scan_inbox()
