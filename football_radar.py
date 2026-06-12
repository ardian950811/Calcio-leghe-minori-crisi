import os
import sys
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

def log_info(message):
    print(f"[*] {message}")

def log_success(message):
    print(f"[+] SUCCESS: {message}")

def log_warning(message):
    print(f"[-] WARNING: {message}")

def clean_teams_list(raw_input):
    log_info("Inizio pulizia del testo incollato da AiScore...")
    lines = raw_input.split('\n')
    cleaned_teams = set()
    
    # Parole da scartare assolutamente per evitare falsi positivi
    trash_keywords = [
        'contattaci', 'termini del servizio', 'informativa sulla privacy', 
        'copyright', 'onescore', 'gamble responsibly', 'sports data provider',
        'vs', 'live', 'lineups', 'standings', 'odds', 'risultati', 'orari'
    ]
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        # Salta i numeri isolati (orari, punteggi, date)
        if line_clean.isdigit():
            continue
            
        # Salta i minuti di gioco (es. 45', 90'+3)
        if "'" in line_clean:
            continue
            
        # Salta la spazzatura del footer o del layout
        if any(trash in line_clean.lower() for trash in trash_keywords):
            continue
            
        # Se supera i controlli, è una squadra valida
        cleaned_teams.add(line_clean)
        
    lista_finale = sorted(list(cleaned_teams))
    log_success(f"Pulizia completata. Rilevate {len(lista_finale)} squadre uniche da scansionare.")
    return lista_finale

def fetch_rss_news(query, engine="google"):
    encoded_query = urllib.parse.quote(f'"{query}"')
    
    if engine == "google":
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    elif engine == "yahoo":
        url = f"https://news.yahoo.com/rss/search?p={encoded_query}"
    else:
        return []

    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
            root = ET.fromstring(html)
            articles = []
            for item in root.findall('.//item'):
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                articles.append({'title': title, 'link': link, 'pubDate': pub_date})
            return articles
    except Exception as e:
        return []

def scan_football_radar():
    # Recupera i dati passati dall'interfaccia web
    raw_teams = os.environ.get("TEAMS_LIST", "")
    telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    if not raw_teams:
        log_warning("Nessuna squadra ricevuta dall'interfaccia web. Esco.")
        sys.exit(0)
        
    teams = clean_teams_list(raw_teams)
    
    # 4 GIORNI DI FINESTRA TEMPORALE (96 ore)
    days_back = 4
    time_threshold = datetime.now() - timedelta(days=days_back)
    log_info(f"Finestra di scansione impostata a: {days_back} giorni (Notizie dal {time_threshold.strftime('%d/%m/%Y')} ad oggi).")
    
    # Vocabolario potenziato in 4 lingue
    keywords = [
        # --- ITALIANO ---
        'sciopero', 'stipendi', 'crisi finanziaria', 'giovani', 'riserves', 'formazione rimaneggiata', 
        'schiererà i giovani', 'spazio alle riserve', 'rosa ridotta', 'infortuni masivi', 'ammutinamento',
        # --- INGLESE ---
        'strike', 'salary', 'unpaid', 'injury', 'unpaid wages', 'boycott', 'financial crisis', 
        'bankruptcy', 'youth squad', 'reserves', 'injury crisis', 'missing players', 'match-fixing', 
        'walkout', 'sidelined', 'scandal', 'will play with reserves', 'forced to play youth', 
        'depleted squad', 'academy players', 'second team', 'b-team', 'under-20',
        # --- SPAGNOLO ---
        'huelga', 'sueldos', 'impagos', 'deudas', 'paro', 'boicot', 'crisis económica', 'quiebra', 
        'juveniles', 'bajas masivas', 'lesiones', 'ausencias', 'suspendidos', 'amaño', 'jugará con suplentes', 
        'obligado a jugar con juveniles', 'plantel diezmado', 'reservas', 'equipo alternativo', 
        'canteranos', 'sub-20', 'equipo de emergencia',
        # --- PORTOGHESE ---
        'greve', 'salários atrasados', 'calote', 'crise financeira', 'desfalques', 'time sub-20', 
        'lesões', 'suspensos', 'manipulação', 'W.O.', 'jogará com reservas', 'forçado a usar a base', 
        'elenco reduzido', 'time alternativo', 'garotos da base',
        # --- FRANCESE ---
        'grève', 'salaires impayés', 'crise financière', 'dettes', 'forfaits', 'hécatombe', 
        'blessures', 'équipe de jeunes', 'suspendus', 'jouera con les réservistes', 'aligner les jeunes', 
        'effectif réduit', 'équipe réserve', 'équipe b'
    ]
    
    crisis_database = []
    
    for idx, team in enumerate(teams, 1):
        log_info(f"[{idx}/{len(teams)}] Scansione in corso per: {team}")
        
        # Cerca su Google News e Yahoo News
        google_news = fetch_rss_news(team, "google")
        yahoo_news = fetch_rss_news(team, "yahoo")
        all_news = google_news + yahoo_news
        
        team_alerts = []
        
        for article in all_news:
            title_lower = article['title'].lower()
            
            # Controllo parole chiave di emergenza
            triggered_keyword = next((kw for kw in keywords if kw in title_lower), None)
            
            if triggered_keyword:
                # Verifica la data della notizia
                try:
                    # Formato standard dei feed RSS: "Fri, 12 Jun 2026 08:00:00 GMT"
                    pub_date_clean = article['pubDate'].split(',')[1].split('GMT')[0].strip()
                    parsed_date = datetime.strptime(pub_date_clean, "%d %b %Y %H:%M:%S")
                except:
                    parsed_date = datetime.now() # Se la data fallisce, la prende per buona per sicurezza
                
                if parsed_date >= time_threshold:
                    alert_data = {
                        'team': team,
                        'title': article['title'],
                        'link': article['link'],
                        'keyword_detected': triggered_keyword,
                        'date': parsed_date.strftime('%Y-%m-%d %H:%M')
                    }
                    if alert_data not in team_alerts:
                        team_alerts.append(alert_data)
        
        if team_alerts:
            log_success(f"🚨 TROVATA CRISI per {team}! {len(team_alerts)} notizie sospette rilevate.")
            crisis_database.extend(team_alerts)
            
            # Invia notifica immediata a Telegram per questa squadra
            if telegram_token and chat_id:
                for alert in team_alerts:
                    msg = (
                        f"🚨 *FOOTBALL CRISIS RADAR* 🚨\n\n"
                        f"⚽️ *Squadra:* {alert['team']}\n"
                        f"⚠️ *Anomalia:* {alert['keyword_detected'].upper()}\n"
                        f"📰 *Notizia:* {alert['title']}\n"
                        f"📅 *Data:* {alert['date']}\n\n"
                        f"🔗 [Leggi la fonte locale]({alert['link']})"
                    )
                    encoded_msg = urllib.parse.quote(msg)
                    telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={encoded_msg}&parse_mode=Markdown"
                    try:
                        urllib.request.urlopen(telegram_url, timeout=5)
                    except Exception as e:
                        log_warning(f"Impossibile inviare il messaggio a Telegram: {e}")
        
        # Pausa di sicurezza per non sovraccaricare i server e prevenire blocchi
        time.sleep(3)
        
    # Salva il report completo nel file JSON della repository
    with open('crisis_report.json', 'w', encoding='utf-8') as f:
        json.dump(crisis_database, f, ensure_ascii=False, indent=4)
    
    log_success(f"Analisi completata. Totale eventi di crisi registrati: {len(crisis_database)}")

if __name__ == "__main__":
    scan_football_radar()
