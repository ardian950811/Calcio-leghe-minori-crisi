import os
import json
import time
import urllib.parse
import requests
from duckduckgo_search import DDGS

def send_telegram_message(token, chat_id, text):
    """Send push notification via Telegram"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram notification sent successfully!")
        else:
            print(f"Telegram error: {response.text}")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def search_team_crisis_ddg(team_name, country_context="global"):
    print(f"Scanning deep web for: {team_name} ({country_context})...")
    
    keywords_dict = {
        "spanish": ['huelga', 'sueldos', 'deuda', 'lesion', 'crisis', 'juveniles', 'reserva', 'suplentes', 'bajas', 'ausencias'],
        "french": ['grève', 'salaire', 'impayé', 'dette', 'blessure', 'crise', 'jeunes', 'réserve', 'remplaçants', 'absences'],
        "english": ['strike', 'salary', 'unpaid', 'debt', 'injury', 'crisis', 'youth team', 'reserves', 'bench players', 'absences'],
        "global": ['strike', 'salary', 'unpaid', 'injury', 'huelga', 'sueldos', 'grève', 'juveniles', 'youth team', 'reserves']
    }
    
    keywords = keywords_dict.get(country_context.lower(), keywords_dict["global"])
    keywords_query = " OR ".join([f'"{kw}"' for kw in keywords])
    full_query = f'"{team_name}" ({keywords_query})'
    
    alerts_found = []
    
    try:
        # Using DuckDuckGo to bypass Google's News filters. 
        # timelimit='w' fetches results from the past week to ensure no weekend news is missed.
        with DDGS() as ddgs:
            results = list(ddgs.text(full_query, timelimit='w', max_results=5))
            
            if results:
                for r in results:
                    alerts_found.append({
                        "title": r.get('title', 'Web Article'),
                        "link": r.get('href', ''),
                        "date": "Recent (Web)"
                    })
    except Exception as e:
        print(f"Error searching DuckDuckGo for {team_name}: {e}")
        
    return alerts_found

def main_investigation():
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    # Test teams - Replace these with the actual niche teams you are monitoring
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
        
        recent_news = search_team_crisis_ddg(name, context)
        report_results[name] = recent_news
        
        if recent_news:
            for news in recent_news:
                new_alerts_detected.append(
                    f"🚨 <b>WEB ALERT: {name}</b>\n"
                    f"📰 {news['title']}\n"
                    f"🔗 <a href='{news['link']}'>Read Article</a>\n"
                )
        
        time.sleep(4) # Anti-ban delay
        
    with open("crisis_report.json", "w", encoding="utf-8") as f:
        json.dump(report_results, f, indent=4)
    print("Website JSON updated with DuckDuckGo Web Search data.")
        
    if new_alerts_detected and telegram_token and telegram_chat_id:
        print(f"Sending {len(new_alerts_detected)} notifications to Telegram...")
        full_message = "\n".join(new_alerts_detected[:10])
        send_telegram_message(telegram_token, telegram_chat_id, full_message)
    else:
        print("No critical web alerts detected recently.")

if __name__ == "__main__":
    main_investigation()
