# 🗑️ Bin Day Notifier

Serverless bin-collection reminder for my address, built entirely on GitHub's
free infrastructure — no server, no phone/PC that needs to stay on.

**Stack:** Python · Regex/HTML parsing · GitHub Actions (scheduled CI/CD) ·
Telegram Bot API · GitHub Secrets

## How it works
1. A GitHub Actions workflow runs every Monday afternoon (NZ time) — the
   evening before Tuesday's usual collection, when the bins need to go
   out.
2. It fetches my council's collection-day page for my specific address,
   using headers that satisfy the site's bot-protection checks
   (`sec-fetch-site: same-origin` + a same-domain `Referer`).
3. The page embeds its collection dates as escaped JSON inside a Next.js
   hydration script rather than plain HTML tables, so the data is pulled
   out with a targeted regular expression instead of CSS selectors.
4. If rubbish, recycling, or food scraps collection falls **tomorrow**, it
   sends a Telegram message with what to put out. Because it only runs
   once a week, it never stays silent: if nothing's due tomorrow (e.g. a
   public holiday pushed the date later), it still messages with the
   actual next collection date(s) instead.
5. If the page can't be reached — see "Notes" below — it falls back to
   sending a Telegram message with a direct link instead, so a reminder
   still arrives either way.
6. Secrets (bot token, chat ID, and the address-specific page URL) are
   stored in GitHub Actions Secrets — never committed to the repo. The
   collection-day URL is address-specific and could reveal a home address,
   so it's treated the same as a credential rather than hardcoded.

## Setup
1. **Create a Telegram bot**: message [@BotFather](https://t.me/BotFather) on
   Telegram → `/newbot` → follow the prompts → copy the token it gives you.
2. **Get your chat ID**: message your new bot anything, then visit
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser →
   find `"chat":{"id": ...}` in the JSON.
3. **Find your own collection-day page URL**: use your council's "find my
   collection day" tool for your address; copy the resulting URL.
4. In this repo: **Settings → Secrets and variables → Actions** → add:
   - `BIN_BOT_TOKEN`
   - `BIN_CHAT_ID`
   - `BIN_COLLECTION_URL` — your address's collection-day page URL
5. Test it manually: **Actions tab → Check bin day → Run workflow**, then
   check the logs.

## Notes
This site's bot-protection (Fastly Bot Management) turned out to be a good
real-world case study in the limits of scraping past anti-bot defenses:

- From a home connection, the exact right headers (`sec-fetch-site:
  same-origin` + a same-domain `Referer`) are enough to get a clean 200.
- GitHub's own hosted runners sit on datacenter IPs that get blocked
  outright, headers or not.
- Tried routing around that with two different scraping proxy services:
  - **ScraperAPI** — its free/trial `premium=true` mode wasn't strong
    enough (500 error); its stronger `ultra_premium=true` mode is
    paid-plan-only (403).
  - **Scrape.do** — `super=true` (residential/mobile proxy, included in
    its free plan) still got a 406. Adding `extraHeaders=true` to forward
    the exact working headers through the proxy: still 406. Adding
    `render=true` (a real headless browser behind the proxy): still 406.
- At that point, getting past it would mean paying for a stronger tier of
  one of these services — not worth it for a personal weekly reminder.
  Instead, the script degrades gracefully: if it can't reach the page for
  any reason, it sends a Telegram message with a direct link instead of
  failing silently, so a reminder still reaches me either way.
- The date-parsing regex is tied to the current structure of the council's
  page. If they redesign it, `parse_collection_dates()` in `scraper.py`
  will need updating — the same fallback message will fire in that case
  too.
