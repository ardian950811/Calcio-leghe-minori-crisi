import os
import sys
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import re

def log_info(message): print(f"[*] {message}")
def log_success(message): print(f"[+] {message}")
def log_warning(message): print(f"[-] {message}")

def clean_teams_list(raw_input):
    log_info("Inizio pulizia del testo...")
    lines = raw_input.split('\n')
    cleaned_teams = set()
    
    for line in lines:
        line = line.strip()
        # 1. Rimuovi orari (es 15:30)
        line = re.sub(r'\d{1,2}:\d{2}', '', line)
        # 2. Rimuovi quote (es 1.85, 3.40)
        line = re.sub(r'\d{1,2}\.\d{2}', '', line)
        # 3. Rimuovi simboli tipici dei palinsesti
        line = re.sub(r'[\-\(\)\[\]]', '', line)
        # 4. Rimuovi parole inutili
        trash = ['vs', 'live', 'lineups', 'standings', 'odds', 'risultati', 'orari', 'team']
        for t in trash:
            line = re.sub(r'\b' + t + r'\b', '', line, flags=re.IGNORECASE)
            
        line = line.strip()
        
        # FILTRO FINALE: deve essere lungo almeno 4 caratteri e non contenere solo numeri
        if len(line) > 3 and not line.replace(" ", "").isdigit():
            cleaned_teams.add(line)
            
    lista_finale = sorted(list(cleaned_teams))
    log_success(f"Pulizia completata. Rilevate {len(lista_finale)} squadre valide.")
    return lista_finale

def fetch_rss_news(team_name):
    # Ricerca precisa
    encoded_query = urllib.parse.quote(f'"{team_name}" football')
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            root = ET.fromstring(response.read())
            articles = []
            for item in root.findall('.//item'):
                title = item.find('title').text
                link = item.find('link').text
                pubDate = item.find('pubDate').text
                
                # FILTRO ESATTO: il nome della squadra DEVE essere nel titolo
                if team_name.lower() in title.lower():
                    articles.append({'title': title, 'link': link, 'pubDate': pubDate})
            return articles
    except Exception as e:
        log_warning(f"Errore recupero news per {team_name}: {e}")
        return []

def scan_football_radar():
    raw_teams = os.environ.get("TEAMS_LIST", "")
    telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    if not raw_teams:
        log_info("Nessun input fornito, skip scansione squadre.")
        teams = []
    else:
        teams = clean_teams_list(raw_teams)
    
    # LISTA AGGIORNATA DELLE VALUE BETS (Crisi, Infortuni, Ammutinamenti)
    keywords = [
        # Infortuni e rosa ridotta
        'injury crisis', 'depleted squad', 'decimated squad', 'plaga de lesiones', 
        'plantel diezmado', 'pocos jugadores disponibles', 'emergenza infortuni', 'rosa decimata',
        
        # Scioperi, boicottaggi e stipendi non pagati
        'boycotting training', 'players strike', 'unpaid wages', 'unpaid salaries',
        'months without pay', 'financial meltdown', 'se niegan a entrenar', 
        'huelga de futbolistas', 'sueldos impagos', 'salarios atrasados', 'crisis económica',
        'sciopero giocatori', 'stipendi non pagati', 'boicottano gli allenamenti',
        
        # Addio dei giocatori chiave
        'players walk out', 'mass exodus', 'key players leave', 'contract terminated',
        'éxodo de jugadores', 'rescindieron contrato', 'referentes abandonan',
        'esodo di giocatori', 'rescissione del contratto',
        
        # Riserve, giovani e turnover
        'forced to play reserves', 'fielding youth team', 'academy players', 'heavy rotation',
        'obligado a jugar con juveniles', 'alinear suplentes', 'jugará con la reserva', 'equipo b', 
        'rotación masiva', 'cuidando titulares', 'squadra riserve', 'in campo la primavera', 'ampio turnover'
    ]
    
    # LISTA IGNORA AGGIORNATA
    ignore_list = [
        'years', 'sentenced', 'lego', 'prison', 'dead', 'gun', 'police', 
        'transfer', 'rumour', 'injury time', 'stoppage time', 'u19', 'u17',
        'calciomercato', 'mercato', 'minuti di recupero'
    ]
    
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
                    
                    # Fix Telegram: invio sicuro senza Markdown
                    if telegram_token and chat_id and team.strip():
                        msg = f"🚨 CRISI: {team}\n⚠️ {triggered.upper()}\n📰 {article['title']}\n🔗 {article['link']}"
                        try:
                            urllib.request.urlopen(f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={urllib.parse.quote(msg)}")
                        except Exception as e:
                            log_warning(f"Errore invio Telegram per {team}: {e}")
        time.sleep(2)
        
    with open('crisis_report.json', 'w', encoding='utf-8') as f:
        json.dump(final_crisis_report, f, ensure_ascii=False, indent=4)
    
    log_success(f"Scansione terminata. Eventi trovati: {len(final_crisis_report['events'])}")

if __name__ == "__main__":
    scan_football_radar()
