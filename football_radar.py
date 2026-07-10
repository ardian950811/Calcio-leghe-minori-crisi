import os
import json
import urllib.parse
import urllib.request
from datetime import datetime
import time
import re

def log_info(message): print(f"[*] {message}")
def log_success(message): print(f"[+] {message}")

def clean_teams_list(raw_input):
    lines = raw_input.split('\n')
    cleaned_teams = set()
    for line in lines:
        line = line.strip()
        # Filtri base: salta vuoti, orari, quote e numeri
        if not line or len(line) <= 2 or ":" in line or re.search(r'\d{1,2}:\d{2}', line): continue
        if re.search(r'^\d+[\.,]\d+$', line) or line.replace(".", "").replace(",", "").isdigit(): continue
        if len(line) > 2 and not line.replace(" ", "").isdigit(): cleaned_teams.add(line)
    return sorted(list(cleaned_teams))

def chiedi_a_gemini(team_name, api_key):
    # Usiamo il modello generativo in modo diretto
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Prompt semplificato
    prompt = f"Trova notizie calcio su '{team_name}' ultime 48 ore. Riassumi in italiano. Se nessuna, rispondi NESSUNA_NOTIZIA."
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        # Rimuoviamo il blocco 'tools' complesso che causava il 404 e lasciamo che Gemini usi il suo ground interno
        "generationConfig": {"temperature": 0.2}
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            risposta_json = json.loads(response.read().decode('utf-8'))
            testo = risposta_json['candidates'][0]['content']['parts'][0]['text']
            return testo.strip(), f"https://www.google.com/search?q={urllib.parse.quote(team_name + ' calcio news')}"
    except Exception as e:
        print(f"    [!] Errore connessione: {e}")
        return "NESSUNA_NOTIZIA", ""

def scan_football_radar():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key: return
    
    raw_teams = os.environ.get("TEAMS_LIST", "")
    teams = clean_teams_list(raw_teams)
    
    report = {"last_check": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "events": []}
    
    for team in teams:
        log_info(f"Analizzo: {team}")
        testo, link = chiedi_a_gemini(team, api_key)
        
        if "NESSUNA_NOTIZIA" not in testo and len(testo) > 5:
            report["events"].append({'team': team, 'title': testo, 'link': link})
            log_success(f"Trovato!")
            
        time.sleep(5) 
        
    with open('crisis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    scan_football_radar()
