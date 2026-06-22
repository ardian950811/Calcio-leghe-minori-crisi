import os
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import re

def log_info(message): print(f"[*] {message}")
def log_success(message): print(f"[+] {message}")

# --- NUOVA FUNZIONE: Traduttore Automatico in Italiano ---
def traduci_in_italiano(testo):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=it&dt=t&q={urllib.parse.quote(testo)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data[0][0][0]
    except Exception as e:
        print(f"Errore di traduzione: {e}")
        return testo # Se la traduzione fallisce, tiene il testo originale

def clean_teams_list(raw_input):
    elementi_da_ignorare = ["diretta", "risultati", "aiscore", "scarica", "pallacanestro", "tennis", "live", "sospesa", "punteggio"]
    rimozioni = [r'\bFC\b', r'\bU20\b', r'\bU21\b', r'\bReserves\b', r'\bRiserve\b', r'\bB\b$']
    
    lines = raw_input.split('\n')
    cleaned_teams = set()
    for line in lines:
        line = line.strip()
        if not line or ":" in line or re.search(r'\d{1,2}:\d{2}', line) or len(line) <= 2: continue
        nome = line
        for r in rimozioni: nome = re.sub(r, '', nome, flags=re.IGNORECASE)
        nome = nome.strip()
        if len(nome) > 2 and not nome.replace(" ", "").isdigit(): cleaned_teams.add(nome)
    return sorted(list(cleaned_teams))

def fetch_all_news(team_name):
    query = f"{team_name} (football OR calcio OR soccer) when:4d"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            root = ET.fromstring(response.read())
            articles = []
            for item in root.findall('.//item'):
                articles.append({
                    'title': item.find('title').text,
                    'link': item.find('link').text
                })
            return articles
    except: return []

def scan_football_radar():
    raw_teams = os.environ.get("TEAMS_LIST", "")
    teams = clean_teams_list(raw_teams) if raw_teams else []
    
    report = {"last_check": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "events": []}
    
    for team in teams:
        print(f"[*] Monitoro: {team}")
        news = fetch_all_news(team)
        for article in news:
            # Traduce il titolo prima di salvarlo!
            titolo_ita = traduci_in_italiano(article['title'])
            report["events"].append({
                'team': team, 
                'title': titolo_ita, 
                'link': article['link']
            })
        time.sleep(1.5)
        
    with open('crisis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
    log_success(f"Monitoraggio completato. Trovate {len(report['events'])} notizie totali.")

if __name__ == "__main__":
    scan_football_radar()
