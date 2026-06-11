import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import time
import os
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
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram notification sent successfully!")
        else:
            print(f"Telegram error: {response.text}")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def search_team_google_news(team_name, country_context="global"):
    print(f"Scanning Google News RSS (last 48h) for: {team_name}...")
    
    # Broad search: just the team name to ensure Google News finds it
    encoded_query = urllib.parse.quote(f'"{team_name}"')
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    keywords_dict = {
        "spanish": ['huelga', 'sueldos', 'deuda', 'lesion', 'crisis', 'juveniles', 'reserva', 'suplentes', 'bajas', 'ausencias', 'problema'],
        "french": ['grève', 'salaire', 'impayé', 'dette', 'blessure', 'crise', 'jeunes', 'réserve', 'remplaçants', 'absences'],
        "english": ['strike', 'salary', 'unpaid', 'debt', 'injury', 'crisis', 'youth team', 'reserves', 'bench players', 'absences', 'missing'],
        "global": ['strike', 'salary', 'unpaid', 'injury', 'huelga', 'sueldos', 'grève', 'juveniles', 'youth team', 'reserves', 'absences']
    }
    
    keywords = keywords_dict.get(country_context.lower(), keywords_dict["global"])
    
    all_team_news = []
    crisis_alerts = []
    time_limit = datetime.now() - timedelta(hours=48)
    
    try:
        response = requests.get(rss_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all('item')
        
        print(f"Raw articles found for {team_name}: {len(items)}")
        
        for item in items:
            title = item.title.text
            link = item.link.text
            pub_date_str = item.pubDate.text
            
            try:
                parsed_date = email.utils.parsedate_to_datetime(pub_date_str)
                parsed_date = parsed_date.replace(tzinfo=None)
            except Exception:
                parsed_date = datetime.now()

            # Filter out articles older than 48 hours
            if parsed_date < time_limit:
                continue
                
            news_data = {
                "title": title,
                "link": link,
                "date": pub_date_str,
                "is_crisis": False
            }
            
            # Smart check: Python checks if any crisis keyword is inside the title (case-insensitive)
            title_lower = title.lower()
            if any(kw in title_lower for kw in keywords):
                news_data["is_crisis"] = True
                crisis_alerts.append(news_data)
                
            all_team_news.append(news_data)
            
    except Exception as e:
        print(f"Error fetching data for {team_name}: {e}")
        
    return all_team_news, crisis_alerts

def main_investigation():
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    # PUT YOUR REAL CHOSEN TEAMS HERE
    teams_to_search = [
        {"name": "Chacarita Juniors", "context": "spanish"},
        {"name": "Gor Mahia", "context": "english"},
        {"name": "USM Alger", "context": "french"}
    ]
    
    report_results = {}
    new_alerts_detected = []
    
    for team in teams_to_search:
        name = team["name"]
        context = team["context"]
        
        all_news, crisis_news = search_team_google_news(name, context)
        
        # We save ALL recent news in the JSON so your website is never empty
        report_results[name] = all_news
        
        # Telegram will trigger ONLY if a crisis keyword was caught by Python
        if crisis_news:
            for news in crisis_news:
                new_alerts_detected.append(
                    f"🚨 <b>CRISIS DETECTED (48h): {name}</b>\n"
                    f"📰 {news['title']}\n"
                    f"🔗 <a href='{news['link']}'>Read Article</a>\n"
                )
        
        time.sleep(2)
        
    with open("crisis_report.json", "w", encoding="utf-8") as f:
        json.dump(report_results, f, indent=4)
    print("Database updated. Website will display the current status.")
        
    if new_alerts_detected and telegram_token and telegram_chat_id:
        print(f"Sending {len(new_alerts_detected)} targeted alerts to Telegram...")
        full_message = "\n".join(new_alerts_detected[:10])
        send_telegram_message(telegram_token, telegram_chat_id, full_message)
    else:
        print("Investigation finished. No critical spikes found in the fetched news.")

if __name__ == "__main__":
    main_investigation()
