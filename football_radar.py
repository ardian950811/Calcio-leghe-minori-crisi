import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import time
import os

def send_telegram_message(token, chat_id, text):
    """Invia una notifica push su Telegram"""
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
            print("Notifica Telegram inviata con successo!")
        else:
            print(f"Errore Telegram: {response.text}")
    except Exception as e:
        print(f"Impossibile inviare messaggio Telegram: {e}")

def search_team_crisis_google_web(team_name, country_context="global"):
    print(f"Scansione GOOGLE WEB (Ultime 48h) per: {team_name}...")
    
    keywords_dict = {
        "spanish": ['huelga', 'sueldos', 'deuda', 'lesion', 'crisis', 'juveniles', 'reserva', 'suplentes', 'bajas', 'ausencias'],
        "french": ['grève', 'salaire', 'impayé', 'dette', 'blessure', 'crise', 'jeunes', 'réserve', 'remplaçants', 'absences'],
        "english": ['strike', 'salary', 'unpaid', 'debt', 'injury', 'crisis', 'youth team', 'reserves', 'bench players', 'absences'],
        "global": ['strike', 'salary', 'unpaid', 'injury', 'huelga', 'sueldos', 'grève', 'juveniles', 'youth team', 'reserves']
    }
    
    keywords = keywords_dict.get(country_context.lower(), keywords_dict["global"])
    keywords_query = " OR ".join([f'"{kw}"' for kw in keywords])
    full_query = f'"{team_name}" ({keywords_query})'
    
    encoded_query = urllib.parse.quote(full_query)
    
    # URL di Google Search Classico con filtro temporale di 2 giorni (&tbs=qdr:d2)
    search_url = f"https://www.google.com/search?q={encoded_query}&tbs=qdr:d2&hl=it"
    
    # Gli diciamo che siamo un browser reale per non farci bloccare
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    alerts_found = []
    
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Google ha risposto con codice {response.status_code}. Salto squadra.")
            return alerts_found
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Cerchiamo i blocchi dei risultati organici di Google
        search_results = soup.find_all('div', class_='g')
        print(f"Trovati {len(search_results)} potenziali risultati indicizzati sul web.")
        
        for result in search_results[:5]: # Prendiamo i primi 5 risultati utili
            link_tag = result.find('a')
            title_tag = result.find('h3')
            
            if link_tag and title_tag:
                title = title_tag.text
                link = link_tag['href']
                
                # Evitiamo di prendere link interni di Google
                if link.startswith("http"):
                    alerts_found.append({
                        "title": title,
                        "link": link,
                        "date": "Ultime 48 ore"
                    })
                    
    except Exception as e:
        print(f"Errore durante lo scraping web per {team_name}: {e}")
        
    return alerts_found

def main_investigation():
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    # METTI QUI LE SQUADRE MINORI REALI DA MONITORARE ORA
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
        
        news_recenti = search_team_crisis_google_web(name, context)
        report_results[name] = news_recenti
        
        if news_recenti:
            for news in news_recenti:
                nuovi_allarmi_rilevati.append(
                    f"🚨 <b>ALLERTA WEB (48h): {name}</b>\n"
                    f"📰 {news['title']}\n"
                    f"🔗 <a href='{news['link']}'>Apri Sito Notizia</a>\n"
                )
        
        time.sleep(5) # Pausa più lunga per non insospettire Google
        
    with open("crisis_report.json", "w", encoding="utf-8") as f:
        json.dump(report_results, f, indent=4)
    print("Sito web aggiornato con i dati di Google Web Search.")
        
    if nuovi_allarmi_rilevati and telegram_token and telegram_chat_id:
        print(f"Inviando {len(nuovi_allarmi_rilevati)} notifiche su Telegram...")
        messaggio_completo = "\n".join(nuovi_allarmi_rilevati[:10]) # Massimo 10 alla volta per non intasare
        send_telegram_message(telegram_token, telegram_chat_id, messaggio_completo)
    else:
        print("Nessun alert rilevato sul web nelle ultime 48 ore.")

if __name__ == "__main__":
    main_investigation()
