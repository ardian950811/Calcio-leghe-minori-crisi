import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import time
import os
import re
from datetime import datetime, timedelta
import email.utils

def send_telegram_message(token, chat_id, text):
    """Send push notification via Telegram"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def load_teams_from_website():
    """Load and clean teams pasted directly from AiScore format"""
    teams = []
    raw_input = os.environ.get("TEAMS_INPUT", "") 
    
    if not raw_input:
        print("No teams received from the website.")
        return teams
        
    lines = raw_input.split('\n')
    for line in lines:
        line = line.strip()
        
        # 1. Skip completely empty lines
        if not line:
            continue
            
        # 2. Skip time formats (e.g., 14:30, 85', HT, FT, Canc, Pen)
        if re.match(r'^(\d{1,2}:\d{2}|\d{1,3}\'|HT|FT|Canc|Postp|Pen|AET)$', line, re.IGNORECASE):
            continue
            
        # 3. Skip scores or odds (e.g., 0 - 0, 1-2, 1.50, +1)
        if re.match(r'^(\d+\s*-\s*\d+|\d+\.\d+|\+\d+)$', line):
            continue
            
        # 4. Skip single characters or common separators
        if len(line) <= 2 and line.upper() in ['V', '-', 'X', '1', '2', 'VS']:
            continue
            
        # If it survives the filters, it's a team name
        teams.append({"name": line, "context": "global"})
        
    # Remove duplicates
    unique_teams = [dict(t) for t in {tuple(d.items()) for d in teams}]
    
    print(f"Extracted {len(unique_teams)} clean team names from raw input.")
    return unique_teams

def search_team_google_news(team_name, country_context="global"):
    print(f"Scanning Google News RSS (last 48h) for: {team_name}...")
    encoded_query = urllib.parse.quote(f'"{team_name}"')
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    keywords = ['strike', 'salary', 'unpaid', 'injury', 'huelga', 'sueldos', 'grève', 'juveniles', 'youth team', 'reserves', 'absences', 'lesion', 'bajas', 'crise']
    
    all_team_news = []
    crisis_alerts = []
    time_limit = datetime.now() - timedelta(hours=48)
    
    try:
        response = requests.get(rss_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all('item')
        
        for item in items:
            title = item.title.text
            link = item.link.text
            pub_date_str = item.pubDate.text
            
            try:
                parsed_date = email.utils.parsedate_to_datetime(pub_date_str).replace(tzinfo=None)
            except:
                parsed_date = datetime.now()

            if parsed_date < time_limit:
                continue
                
            news_data = {"title": title, "link": link, "date": pub_date_str, "is_crisis": False}
            
            if any(kw in title.lower() for kw in keywords):
                news_data["is_crisis"] = True
                crisis_alerts.append(news_data)
                
            all_team_news.append(news_data)
    except Exception as e:
        print(f"Error fetching data: {e}")
        
    return all_team_news, crisis_alerts

def main_investigation():
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    teams_to_search = load_teams_from_website()
    
    if not teams_to_search:
        return
        
    report_results = {}
    new_alerts_detected = []
    
    for team in teams_to_search:
        name = team["name"]
        all_news, crisis_news = search_team_google_news(name, team["context"])
        
        if all_news:
            report_results[name] = all_news
        
        if crisis_news:
            for news in crisis_news:
                new_alerts_detected.append(
                    f"🚨 <b>CRISIS DETECTED: {name}</b>\n📰 {news['title']}\n🔗 <a href='{news['link']}'>Read Article</a>\n"
                )
        time.sleep(3) 
        
    with open("crisis_report.json", "w", encoding="utf-8") as f:
        json.dump(report_results, f, indent=4)
        
    if new_alerts_detected and telegram_token and telegram_chat_id:
        for i in range(0, len(new_alerts_detected), 5):
            chunk = new_alerts_detected[i:i+5]
            send_telegram_message(telegram_token, telegram_chat_id, "\n".join(chunk))
            time.sleep(2)

if __name__ == "__main__":
    main_investigation()
