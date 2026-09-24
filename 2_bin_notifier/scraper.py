"""
Bin Day Notifier
-----------------
Runs once a week (Monday afternoon — see .github/workflows/check.yml) and
sends a Telegram message about the upcoming bin collection, since that's
when I put the bins out for Tuesday's usual collection.

Reads the date the council website currently displays (rather than
assuming a fixed weekday), so public-holiday shifts are picked up
automatically. Because this only runs once a week, it always sends a
message — either "collection is tomorrow", the actual next date(s) if
they've shifted, or a fallback link if the page can't be reached.

The council site's bot-protection (Fastly) blocks automated requests from
cloud/datacenter IPs — including GitHub's own hosted runners — even with
headers that work perfectly from a home connection. Two different
third-party scraping proxies (ScraperAPI, Scrape.do — including residential
IPs, forwarded headers, and full headless-browser rendering) were tried and
still got blocked, so paying for a stronger tier was the only remaining
option to fetch the page automatically from GitHub Actions. Rather than do
that for a personal project, the script instead fails gracefully: if it
can't reach the page, it sends a Telegram message with a direct link
instead, so a reminder still reaches you either way.
"""

import os
import re
import sys
from datetime import date, datetime, timedelta

import requests

# The address-specific page URL is kept out of the repo (it identifies my
# home address) and passed in as a GitHub Actions secret instead. See
# README.md for how to set BIN_COLLECTION_URL.
URL = os.environ.get("BIN_COLLECTION_URL")

# These headers get past Fastly's 406 block when running from a normal
# (non-datacenter) connection: sec-fetch-site must be "same-origin" and a
# same-domain Referer is needed, simulating arriving from the site's own
# address-lookup tool rather than a direct/bot request.
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-NZ,en;q=0.9",
    "cache-control": "max-age=0",
    "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "referer": "https://www.aucklandcouncil.govt.nz/en/rubbish-recycling/rubbish-recycling-collections/rubbish-recycling-collection-days.html",
}

TELEGRAM_TOKEN = os.environ.get("BIN_BOT_TOKEN")
BIN_CHAT_ID = os.environ.get("BIN_CHAT_ID")

# Maps the site's internal icon name to our own keys
ICON_TO_KEY = {
    "rubbish": "rubbish",
    "food-waste": "food_scraps",
    "recycle": "recycling",
}

# Matches blocks like:
# "icon":{"icon":"rubbish"},"children":["Rubbish: ",["$","b",null,{"children":"Tuesday, 15 September"}]]
# (as embedded, escaped JSON inside the page's Next.js hydration script)
PATTERN = re.compile(
    r'\\"icon\\":\\"(rubbish|food-waste|recycle)\\".*?\\"children\\":\\"'
    r'(\w+day),\s+(\d{1,2})\s+(\w+)\\"',
)


def fetch_page() -> str:
    if not URL:
        raise RuntimeError("Missing BIN_COLLECTION_URL secret/environment variable.")

    resp = requests.get(URL, headers=HEADERS, timeout=20)

    if resp.status_code != 200:
        # Save the response so the workflow can upload it as a debug artifact
        with open("debug_response.html", "w", encoding="utf-8") as f:
            f.write(f"Status: {resp.status_code}\n\n{resp.text}")
        resp.raise_for_status()
    return resp.text


def parse_collection_dates(html: str) -> dict:
    today = date.today()
    result = {}
    for icon, weekday_name, day_num, month_name in PATTERN.findall(html):
        key = ICON_TO_KEY[icon]
        # "15 September" has no year -> assume the current year, and if
        # that date already fell more than ~6 months in the past, assume
        # it's next year (covers checking a January date back in December).
        text = f"{day_num} {month_name} {today.year}"
        parsed = datetime.strptime(text, "%d %B %Y").date()
        if parsed < today - timedelta(days=180):
            parsed = parsed.replace(year=parsed.year + 1)
        result[key] = parsed
    return result


def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not BIN_CHAT_ID:
        print("Missing BIN_BOT_TOKEN / BIN_CHAT_ID secrets.", file=sys.stderr)
        sys.exit(1)
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(
        api_url,
        data={"chat_id": BIN_CHAT_ID, "text": message},
        timeout=10,
    )
    resp.raise_for_status()


EXPECTED_KEYS = {"rubbish", "food_scraps", "recycling"}


def main():
    try:
        html = fetch_page()
    except (requests.exceptions.RequestException, RuntimeError) as e:
        # The council site blocks automated requests from GitHub's hosted
        # runners. Rather than failing silently, fall back to sending a
        # direct link so the reminder still shows up.
        print(f"Could not fetch the page automatically: {e}", file=sys.stderr)
        if not URL:
            print("No BIN_COLLECTION_URL configured — can't build a fallback link.", file=sys.stderr)
            sys.exit(1)
        fallback = (
            f"🗑️ Couldn't check your bin day automatically today. "
            f"Visit this link to see your next collection day: {URL}"
        )
        send_telegram(fallback)
        return

    collections = parse_collection_dates(html)

    missing = EXPECTED_KEYS - collections.keys()
    if missing:
        alert = (
            f"⚠️ Bin Day Notifier: couldn't find {', '.join(sorted(missing)) or 'any'} "
            f"collection date(s). The council site's structure may have changed — "
            f"check parse_collection_dates() in scraper.py."
        )
        print(alert, file=sys.stderr)
        send_telegram(alert)
        if not collections:
            return

    print("Dates found:", collections)

    tomorrow = date.today() + timedelta(days=1)
    due_tomorrow = [
        name.replace("_", " ").title()
        for name, d in collections.items()
        if d == tomorrow
    ]

    if due_tomorrow:
        msg = f"🗑️ Put out: {', '.join(due_tomorrow)} — collection is tomorrow ({tomorrow:%A %d %b})."
    else:
        # This only runs once a week (Monday afternoon), so it must always
        # say something useful rather than staying silent — e.g. a public
        # holiday can push the actual date later than "tomorrow".
        by_date = sorted(collections.items(), key=lambda item: item[1])
        details = ", ".join(f"{name.replace('_', ' ').title()}: {d:%A %d %b}" for name, d in by_date)
        msg = f"🗑️ Checked your bin day — next collection(s): {details}."

    print(msg)
    send_telegram(msg)


if __name__ == "__main__":
    main()
