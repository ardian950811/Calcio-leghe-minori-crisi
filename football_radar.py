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
        
        # 1. Salta righe vuote o troppo corte
        if not line or len(line) <= 2: continue
        
        # 2. Salta gli orari (es. 15:30) o punteggi con i due punti
        if ":" in line or re.search(r'\d{1,2}:\d{2}', line): continue
        
        # 3. FIX: Salta quote o numeri decimali (es. 1.03, 2.5, 12.0)
        if re.search(r'^\d+[\.,]\d+$', line) or line.replace(".", "").replace(",", "").isdigit(): continue
        
        # 4. Salta parole chiave di disturbo
        if any(ignore_word.lower() in line.lower() for ignore_word in elementi_da_ignorare):
            continue

        nome = line
        for r in rimovizioni: 
            nome = re.sub(r, '', nome, flags=re.IGNORECASE)
        
        nome = nome.strip()
        # Un ulteriore controllo per essere sicuri che non sia rimasto un numero puro
        if len(nome) > 2 and not nome.replace(" ", "").isdigit(): 
            cleaned_teams.add(nome)
            
    return sorted(list(cleaned_teams))

def chiedi_a_gemini(team_name, api_key):
    # CORREZIONE URL: Usiamo la versione v1 stabile per evitare il 404
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
Sei un analista calcistico professionale. Usa Google Search per cercare in rete le notizie di CALCIO degli ultimi 2 giorni riguardanti la squadra "{team_name}".
Regola 1: IGNORA le notizie non sportive (incidenti, politica locale).
Regola 2: Fai un brevissimo riassunto in italiano (massimo 2 frasi) di quello che sta succedendo.
Regola 3: Se non trovi nessuna notizia calcistica recente su questa specifica squadra, rispondi SOLO ed ESATTAMENTE con la parola "NESSUNA_NOTIZIA".
"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2}
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            risposta_json = json.loads(response.read().decode('utf-8'))
            testo = risposta_json['candidates'][0]['content']['parts'][0]['text']
            
            link_ricerca = f"https://www.google.com/search?q={urllib.parse.quote(team_name + ' football news')}"
            
            return testo.strip(), link_ricregex
    except Exception as e:
        print(f"    [!] Errore connessione Gemini per {team_name}: {e}")
        return "NESSUNA_NOTIZIA", ""

def scan_football_radar():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[!] ERRORE: GEMINI_API_KEY non trovata su GitHub Secrets!")
        return

    raw_teams = os.environ.get("TEAMS_LIST", "")
    teams = clean_teams_list(raw_teams) if raw_teams else []
    
    # Vedrai subito nei log se il filtro ha ripulito le quote!
    log_info(f"Squadre reali trovate dopo aver rimosso le quote: {len(teams)}")
    print(teams)
    
    report = {"last_check": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "events": []}
    
    for team in teams:
        log_info(f"Chiedo a Gemini di cercare notizie calcistiche per: {team}...")
        testo_notizia, link = chiedi_a_gemini(team, api_key)
        
        if "NESSUNA_NOTIZIA" not in testo_notizia and len(testo_notizia) > 5:
            report["events"].append({
                'team': team, 
                'title': testo_notizia, 
                'link': link
            })
            log_success(f"Notizia inserita per {team}!")
        else:
            print(f"    Nessuna notizia calcistica trovata per {team}.")
            
        # Pausa di 5 secondi per rispettare i limiti gratuiti delle API di Google
        time.sleep(5) 
        
    with open('crisis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
        
    log_success(f"Analisi Gemini completata. Trovate notizie per {len(report['events'])} squadre.")

if __name__ == "__main__":
    scan_football_radar()
