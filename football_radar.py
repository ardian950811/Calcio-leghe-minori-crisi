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
        line = re.sub(r'\d{1,2}:\d{2}', '', line)
        line = re.sub(r'\d{1,2}\.\d{2}', '', line)
        line = re.sub(r'[\-\(\)\[\]]', '', line)
        
        trash = ['vs', 'live', 'lineups', 'standings', 'odds', 'risultati', 'orari', 'team']
        for t in trash:
            line = re.sub(r'\b' + t + r'\b', '', line, flags=re.IGNORECASE)
            
        line = line.strip()
        if len(line) > 3 and not line.replace(" ", "").isdigit():
            cleaned_teams.add(line)
            
    lista_finale = sorted(list(cleaned_teams))
    log_success(f"Pulizia completata. Rilevate {len(lista_finale)} squadre valide.")
    return lista_finale

def fetch_rss_news(team_name):
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
    
    # LE TUE 10 TIPOLOGIE DI NOTIZIE ESATTE
    keywords = [
        # 1. Squadra con tanti infortuni
        'injury crisis', 'plaga de lesiones', 'multiple injuries', 'muchas lesiones',
        
        # 2. Giocatori boicottano allenamenti
        'boycotting training', 'boycott training', 'se niegan a entrenar', 'boicot a los entrenamientos',
        
        # 3. Sciopero per mancato pagamento dei stipendi
        'players strike', 'strike over unpaid', 'huelga por falta de pago', 'huelga de jugadores', 'greve de jogadores',
        
        # 4. Stipendi arretrati
        'unpaid wages', 'unpaid salaries', 'salarios atrasados', 'sueldos impagos', 
        
        # 5. Squadra con pochi giocatori in rosa per problemi
        'depleted squad', 'only available players', 'pocos jugadores disponibles', 'plantel reducido', 'bare bones squad',
        
        # 6. Pilastri hanno abbandonato la squadra
        'key players leave', 'players walk out', 'mass exodus', 'referentes abandonan', 'éxodo de jugadores', 'rescindieron contrato',
        
        # 7. Squadra costretta a giocare con le riserve (per infortuni o fughe)
        'forced to play reserves', 'fielding reserve team', 'obligado a jugar con suplentes', 'jugará con la reserva', 'alinear suplentes',
        
        # 8. Squadra costretta a giocare con i giovani (per infortuni o assenze)
        'forced to play youth', 'fielding youth team', 'academy players', 'playing with kids', 'obligado a jugar con juveniles', 'canteranos',
        
        # 9. Crisi economica, pagate poche mensilità
        'financial crisis', 'economic crisis', 'months without pay', 'meses sin cobrar', 'crisis económica', 'unpaid for months',
        
        # 10. Squadra schiera squadra B o giovani perché non è partita importante (Turnover)
        'heavy rotation', 'resting key players', 'unimportant match', 'rotación masiva', 'cuidando titulares', 'equipo alternativo', 'playing b team'
    ]
    
    ignore_list = [
        'years', 'sentenced', 'lego', 'prison', 'dead', 'gun', 'police', 
        'transfer', 'rumour', 'injury time', 'stoppage time', 'u19', 'u17', 'mercato'
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
