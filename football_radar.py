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
    elementi_da_ignorare = ["diretta", "risultati", "aiscore", "scarica", "pallacanestro", "tennis", "live", "sospesa", "punteggio"]
    rimozioni = [r'\bFC\b', r'\bU20\b', r'\bU21\b', r'\bReserves\b', r'\bRiserve\b', r'\bB\b$']
    
    lines = raw_input.split('\n')
    cleaned_teams = set()
    for line in lines:
        line = line.strip()
        
        if not line or len(line) <= 2: continue
        if ":" in line or re.search(r'\d{1,2}:\d{2}', line): continue
        if re.search(r'^\d+[\.,]\d+$', line) or line.replace(".", "").replace(",", "").isdigit(): continue
        
        if any(ignore_word.lower() in line.lower() for ignore_word in elementi_da_ignorare):
            continue

        nome = line
        for r in rimovizioni: 
            nome = re.sub(r, '', nome, flags=re.IGNORECASE)
        
        nome = nome.strip()
        if len(nome) > 2 and not nome.replace(" ", "").isdigit(): 
            cleaned_teams.add(nome)
            
    return sorted(list(cleaned_teams))

def chiedi_a_gemini(team_name, api_key):
    # FIX: Endpoint v1 stabile con sintassi corretta per evitare il 404
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"Trova le ultime notizie di calcio (football news) degli ultimi 2 giorni sulla squadra '{team_name}'. Fai un breve riassunto in italiano di massimo due frasi. Se non trovi notizie recenti su questa squadra, rispondi solo con la parola NESSUNA_NOTIZIA."
    
    # Struttura del payload standard e pulita
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            risposta_json = json.loads(response.read().decode('utf-8'))
            testo = risposta_json['candidates'][0]['content']['parts'][0]['text']
            link_ricerca = f"https://www.google.com/search?q={urllib.parse.quote(team_name + ' calcio notizie')}"
            return testo.strip(), link_ricerca
    except Exception as e:
        print(f"    [!] Errore connessione: {e}")
        return "NESSUNA_NOTIZIA", ""

def scan_football_radar():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[!] ERRORE: GEMINI_API_KEY non trovata nei Secrets di GitHub!")
        return

    raw_teams = os.environ.get("TEAMS_LIST", "")
    teams = clean_teams_list(raw_teams) if raw_teams else []
    
    log_info(f"Squadre da analizzare: {len(teams)}")
    
    report = {"last_check": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "events": []}
    
    for team in teams:
        log_info(f"Analizzo: {team}")
        testo, link = chiedi_a_gemini(team, api_key)
        
        if "NESSUNA_NOTIZIA" not in testo and len(testo) > 5:
            report["events"].append({
                'team': team, 
                'title': testo, 
                'link': link
            })
            log_success(f"Notizia salvata per {team}!")
        else:
            print(f"    Nessuna notizia rilevante.")
            
        # Pausa di 4 secondi per rispettare i limiti della versione gratuita
        time.sleep(4) 
        
    with open('crisis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
        
    log_success(f"Completato! Trovate notizie per {len(report['events'])} squadre.")

if __name__ == "__main__":
    scan_football_radar()
