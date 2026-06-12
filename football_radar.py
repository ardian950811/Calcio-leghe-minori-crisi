import os
import sys
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import time

def log_info(message): print(f"[*] {message}")

def clean_teams_list(raw_input):
    lines = raw_input.split('\n')
    cleaned_teams = set()
    trash = ['vs', 'live', 'lineups', 'standings', 'odds', 'risultati', 'orari']
    for line in lines:
        line_clean = line.strip()
        if line_clean and not line_clean.isdigit() and "'" not in line_clean:
            if not any(t in line_clean.lower() for t in trash):
                cleaned_teams.add(line_clean)
    return sorted(list(cleaned_teams))

def fetch_rss_news(query):
    encoded_query = urllib.parse.quote(f'"{query}" football')
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            root = ET.fromstring(response.read())
            return [{'title': item.find('title').text, 'link': item.find('link').text, 'pubDate': item.find('pubDate').text} 
                    for item in root.findall('.//item')]
    except: return []

def scan_football_radar():
    raw_teams = os.environ.get("TEAMS_LIST", "")
    telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    # Se non c'è input (cron job), usiamo una lista vuota o gestiamo l'uscita
    if not raw_teams:
        log_info("Nessun input fornito, skip scansione squadre.")
        teams = []
    else:
        teams = clean_teams_list(raw_teams)
    
    keywords = ['strike', 'salary', 'unpaid', 'injury', 'youth squad', 'reserves', 'boycott', 'huelga', 'impagos', 'greve']
    ignore_list = ['years', 'sentenced', 'lego', 'prison', 'dead', 'gun', 'police']
    
    final_crisis_report = {
        "last_check": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "events": []
    }
    
    for team in teams:
        all_news = fetch_rss_news(team)
        for article in all_news:
            title_lower = article['title'].lower()
            if any(ign in title_lower for ign in ignore_list): continue
            triggered = next((kw for kw in keywords if kw in title_lower), None)
            
            if triggered:
                alert_data = {'team': team, 'title': article['title'], 'link': article['link'], 'keyword': triggered}
                if alert_data not in final_crisis_report["events"]:
                    final_crisis_report["events"].append(alert_data)
                    
                    if telegram_token and chat_id:
                        msg = f"🚨 *CRISI:* {team}\n⚠️ {triggered.upper()}\n📰 {article['title']}"
                        urllib.request.urlopen(f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={urllib.parse.quote(msg)}&parse_mode=Markdown")
        time.sleep(2)
        
    with open('crisis_report.json', 'w', encoding='utf-8') as f:
        json.dump(final_crisis_report, f, ensure_ascii=False, indent=4)
    
    log_info(f"Scansione terminata. Eventi trovati: {len(final_crisis_report['events'])}")

if __name__ == "__main__":
    scan_football_radar()
