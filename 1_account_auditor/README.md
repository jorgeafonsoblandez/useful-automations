# 🛡️ Local-First Account & Subscription Auditor

Have you ever wondered how many random companies have your email address, or how many newsletters you are subscribed to? 

Instead of using services like *Unroll.me* (which read and sell your data to third parties), this open-source Python script runs **100% locally on your machine**. It securely connects to your inbox, extracts the top domains sending you automated emails, and then uses Google's Gemini AI to generate a Markdown report with direct links to **Delete your Account** or **Unsubscribe**.

## ✨ Features
- **Privacy First:** Connects directly via IMAP. Your emails never leave your computer.
- **Lightning Fast:** Uses batched IMAP fetching to process 1,000 emails in seconds.
- **AI Action Plan:** Automatically finds the exact account deletion URLs for the companies holding your data.

## 🚀 How to Use

### 1. Get your secure credentials
* **App Password:** Do NOT use your standard email password. If you use Gmail, go to **Google Account -> Security -> 2-Step Verification -> App Passwords** and generate a 16-letter password.
* **Gemini API Key:** Get a free AI key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 2. Setup the environment
Rename the `.env.example` file to `.env` and paste your credentials into it:
```env
IMAP_SERVER=imap.gmail.com
EMAIL_ACCOUNT=your_email@gmail.com
APP_PASSWORD=your_16_digit_app_password
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run the Auditor
Open your terminal in this folder and run:
```bash
# Install the required libraries
pip install -r requirements.txt

# Run the scanner
python scanner.py
```

*(Note for Windows users: If `pip` or `python` are not recognized, use `py -m pip install -r requirements.txt` and `py scanner.py`).*

### 4. Clean up your footprint!
Once the script finishes, it will generate an `audit_report.md` file in the same folder. Open it to find your personalized account deletion links!
