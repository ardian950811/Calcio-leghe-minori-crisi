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
        
        # Rimozione sigle societarie e giovanili invasive
        sigle = [r'\bFC\b', r'\bCF\b', r'\bCD\b', r'\bCA\b', r'\bUD\b', r'\bAC\b', r'\bU20\b', r'\bU23\b', r'\bAtl\b', r'\bAtletico\b']
        for s in sigle:
            line = re.sub(s, '', line, flags=re.IGNORECASE)
            
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
    # Rimosse le virgolette fisse per dare massima libertà di indicizzazione a Google
    query = f"{team_name} (football OR futbol OR futebol OR calcio OR soccer)"
    encoded_query = urllib.parse.quote(query)
    
    url = f"https://news.google.com/rss/search?q={encoded_query}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            root = ET.fromstring(response.read())
            articles = []
            
            items = root.findall('.//item')
            # DIAGNOSTICA: Stampa nei log quante notizie grezze vede Google per questa squadra
            if len(items) == 0:
                print(f"    -> [VUOTO] Google News ha risposto con 0 risultati totali per: {team_name}")
            else:
                print(f"    -> Google News ha trovato {len(items)} notizie generiche per: {team_name}")
            
            parole = [p for p in team_name.split() if len(p) > 3]
            parola_chiave_squadra = max(parole, key=len).lower() if parole else team_name.lower()
            
            for item in root.findall('.//item'):
                title = item.find('title').text
                link = item.find('link').text
                pubDate = item.find('pubDate').text
                
                if parola_chiave_squadra in title.lower():
                    articles.append({'title': title, 'link': link, 'pubDate': pubDate})
            return articles
    except Exception as e:
        log_warning(f"Errore di connessione/blocco per {team_name}: {e}")
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
    
    keywords = [
        'injury crisis', 'plaga de lesiones', 'multiple injuries', 'muchas lesiones', 'emergenza infortuni', 'rosa decimata',
        'boycotting training', 'boycott training', 'se niegan a entrenar', 'boicot a los entrenamientos', 'boicottano gli allenamenti',
        'players strike', 'strike over unpaid', 'huelga por falta de pago', 'huelga de jugadores', 'greve de jogadores', 'sciopero giocatori',
        'unpaid wages', 'unpaid salaries', 'salarios atrasados', 'sueldos impagos', 'stipendi non pagati', 'debito con el plantel',
        'depleted squad', 'only available players', 'pocos jugadores disponibles', 'plantel reducido', 'bare bones squad', 'rosa ridotta all osso',
        'key players leave', 'players walk out', 'mass exodus', 'referentes abandonan', 'éxodo de jugadores', 'rescindieron contrato', 'esodo di giocatori', 'rescissione del contratto', 'abbandonano il club', 'mass departure', 'free agents', 'contratto risolto',
        'forced to play reserves', 'fielding reserve team', 'obligado a jugar con suplentes', 'jugará con la reserva', 'alinear suplentes', 'squadra riserve',
        'forced to play youth', 'fielding youth team', 'academy players', 'playing with kids', 'obligado a jugar con juveniles', 'canteranos', 'in campo la primavera',
        'financial crisis', 'economic crisis', 'months without pay', 'meses sin cobrar', 'crisis económica', 'unpaid for months', 'fallimento', 'bankruptcy', 'quiebra', 'financial meltdown',
        'heavy rotation', 'resting key players', 'unimportant match', 'rotación masiva', 'cuidando titulares', 'equipo alternativo', 'playing b team', 'ampio turnover',
        'vestuario roto', 'locker room crisis', 'spogliatoio spaccato', 'broken dressing room', 'internal war', 'crisis interna',
        'travel chaos', 'bus broke down', 'stranded at airport', 'arrived late', 'caos logístico', 'micro averiado', 'llegada tardía', 'varados', 'ônibus quebrado', 'atraso no voo',
        'virus outbreak', 'food poisoning', 'flu epidemic', 'players ill', 'intoxicación masiva', 'brote di virus', 'jugadores enfermos', 'cuadro viral', 'intoxicação alimentar',
        'fans protest', 'attacked by fans', 'training interrupted', 'apretada de la barra', 'protesta di hinchas', 'clima tenso', 'minacce ultras', 'agredidos por hinchas', 'treino invadido'
    ]
    
    ignore_list = [
        'years', 'sentenced', 'lego', 'prison', 'dead', 'gun', 'police', 
        'transfer', 'rumour', 'injury time', 'stoppage time', 'u19', 'u17', 'mercato', 'calciomercato'
    ]
    
    final_crisis_report = {
        "last_check": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "events": []
    }
    
    for team in teams:
        print(f"[*] Analizzo: {team}")
        all_news = fetch_rss_news(team)
        
        for article in all_news:
            title_lower = article['title'].lower()
            if any(ign in title_lower for ign in ignore_list): continue
            triggered = next((kw for kw in keywords if kw in title_lower), None)
            
            if triggered:
                print(f"    🚨 TROVATA CRISI PER {team}! Parola chiave: {triggered}")
                alert_data = {'team': team, 'title': article['title'], 'link': article['link'], 'keyword': triggered}
                if alert_data not in final_crisis_report["events"]:
                    final_crisis_report["events"].append(alert_data)
                    
                    if telegram_token and chat_id and team.strip():
                        msg = f"🚨 CRISI: {team}\n⚠️ {triggered.upper()}\n📰 {article['title']}\n🔗 {article['link']}"
                        try:
                            urllib.request.urlopen(f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={urllib.parse.quote(msg)}")
                        except Exception as e:
                            log_warning(f"Errore invio Telegram per {team}: {e}")
        time.sleep(2.0) # Aumentato leggermente per simulare un comportamento umano ed evitare i blocchi di Google
        
    with open('crisis_report.json', 'w', encoding='utf-8') as f:
        json.dump(final_crisis_report, f, ensure_ascii=False, indent=4)
    
    log_success(f"Scansione terminata. Eventi trovati: {len(final_crisis_report['events'])}")

if __name__ == "__main__":
    scan_football_radar()
