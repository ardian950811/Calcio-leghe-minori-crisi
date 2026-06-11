import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import time
import os
from datetime import datetime, timedelta
import email.utils

def send_telegram_message(token, chat_id, text):
    """Invia una notifica push su Telegram"""
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
            print("Notifica Telegram inviata con successo!")
        else:
            print(f"Errore Telegram: {response.text}")
    except Exception as e:
        print(f"Impossibile inviare messaggio Telegram: {e}")

def search_team_crisis_news(team_name, country_context="global"):
    print(f"Scansione notizie di crisi (ultime 48h) per: {team_name} ({country_context})...")
    
    keywords_dict = {
        "spanish": ['huelga', 'sueldos', 'deuda', 'lesion', 'crisis', 'problema', 'no entrena', 'juveniles', 'reserva', 'suplentes', 'bajas', 'ausencias', 'titulares descansan'],
        "french": ['grève', 'salaire', 'impayé', 'dette', 'blessure', 'crise', 'boycott', 'jeunes', 'réserve', 'remplaçants', 'absences', 'forfait', 'équipe B'],
        "english": ['strike', 'salary', 'unpaid', 'debt', 'injury', 'crisis', 'boycott', 'protest', 'youth team', 'reserves', 'bench players', 'absences', 'missing players', 'rested'],
        "global": ['strike', 'salary', 'unpaid', 'injury', 'huelga', 'sueldos', 'grève', 'juveniles', 'youth team', 'reserves', 'reserva', 'suplentes', 'absences']
    }
    
    keywords = keywords_dict.get(country_context.lower(), keywords_dict["global"])
    keywords_query = " OR ".join([f'"{kw}"' for kw in keywords])
    full_query = f'"{team_name}" ({keywords_query})'
    
    encoded_query = urllib.parse.quote(full_query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    alerts_found = []
    # MODIFICA: Accettiamo notizie pubblicate nelle ultime 48 ore
    limite_tempo = datetime.now() - timedelta(hours=48)
    
    try:
        response = requests.get(rss_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all('item')
        
        for item in items:
            title = item.title.text
            link = item.link.text
            pub_date_str = item.pubDate.text
            
            try:
                parsed_date = email.utils.parsedate_to_datetime(pub_date_str)
                parsed_date = parsed_date.replace(tzinfo=None)
            except Exception:
                parsed_date = datetime.now()

            # FILTRO AGGIORNATO: Ignora solo se più vecchia di due giorni (48 ore)
            if parsed_date < limite_tempo:
                continue
                
            alerts_found.append({
                "title": title,
                "link": link,
                "date": pub_date_str
            })
            
    except Exception as e:
        print(f"Errore durante la ricerca per {team_name}: {e}")
        
    return alerts_found

def main_investigation():
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    # Inserisci qui le squadre reali che vuoi monitorare stasera o nel weekend
    teams_to_search = [
        {"name": "Chacarita Juniors", "context": "spanish"},
        {"name": "Gor Mahia", "context": "english"},
        {"name": "USM Alger", "context": "french"}
    ]
    
    report_results = {}
    nuovi_allarmi_rilevati = []
    
    for team in teams_to_search:
        name = team["name"]
        context = team["context"]
        
        news_recenti = search_team_crisis_news(name, context)
        report_results[name] = news_recenti
        
        if news_recenti:
            for news in news_recenti:
                nuovi_allarmi_rilevati.append(
                    f"🚨 <b>CRISI RILEVATA (Ultime 48h): {name}</b>\n"
                    f"📰 {news['title']}\n"
                    f"🔗 <a href='{news['link']}'>Leggi Articolo</a>\n"
                )
        
        time.sleep(2)
        
    with open("crisis_report.json", "w", encoding="utf-8") as f:
        json.dump(report_results, f, indent=4)
    print("Sito web aggiornato con i dati delle ultime 48 ore.")
        
    if nuovi_allarmi_rilevati and telegram_token and telegram_chat_id:
        print(f"Trovati {len(nuovi_allarmi_rilevati)} alert utili. Invio su Telegram...")
        messaggio_completo = "\n".join(nuovi_allarmi_rilevati)
        send_telegram_message(telegram_token, telegram_chat_id, messaggio_completo)
    else:
        print("Nessuna notizia critica nelle ultime 48 ore o bot non configurato.")

if __name__ == "__main__":
    main_investigation()
