import re

def pulisci_testo_aiscore(testo_grezzo):
    # Lista di parole chiave strutturali e sporcizia da scartare a monte
    elementi_da_ignorare = [
        "diretta calcio", "risultati calcio", "aiscore", "scarica", "coppa del mondo",
        "pallacanestro", "tennis", "altro", "fav", "tutto", "in corso", "finito", 
        "programma", "imminente", "live", "streaming", "gratis", "contattaci", 
        "termini del servizio", "informativa sulla privacy", "copyright", "gamble",
        "punteggio", "prossima partita", "partite di oggi", "visita", "onescore"
    ]
    
    # Sigle calcistiche o giovanili da rimuovere dai nomi per ottimizzare la ricerca su Google News
    rimozioni_squadre = [
        r'\bFC\b', r'\bU20\b', r'\bU21\b', r'\bU17\b', r'\bU19\b', r'\bYouth\b',
        r'\bReserves\b', r'\bRiserve\b', r'\bRiserva\b', r'\(femminile\)', r'\bB\b$'
    ]
    
    righe = testo_grezzo.split('\n')
    squadre_rilevate = set()
    
    for riga in righe:
        riga_pulita = riga.strip()
        
        # 1. Salta righe vuote o con emoji singole dell'interfaccia
        if not riga_pulita or riga_pulita == "￼":
            continue
            
        # 2. Salta i blocchi di intestazione campionato (es. "Argentina : Lega della Riserva")
        if ":" in riga_pulita:
            continue
            
        # 3. Salta orari (es. "11:00", "12:00") e minutaggi intermedi (es. "25 '", "70 '")
        if re.search(r'\d{1,2}:\d{2}', riga_pulita) or re.search(r'\d{1,2}\s*\'', riga_pulita):
            continue
            
        # 4. Salta i numeri isolati (es. punteggi, ID interni come "9999", "1086" o quote come "2.15")
        # Riconosce cifre intere o decimali separati da punto
        riga_senza_spazi = riga_pulita.replace(" ", "")
        if riga_senza_spazi.isdigit() or re.match(r'^\d+\.\d+$', riga_senza_spazi):
            continue
            
        # 5. Salta le parole chiave del menu di sistema o del sito web
        if any(parola in riga_pulita.lower() for parola in elementi_da_ignorare):
            continue
            
        # 6. Salta righe di testo descrittive troppo corte (es. "-", "vs")
        if len(riga_pulita) <= 2:
            continue
            
        # --- SEZIONE PULIZIA SQUADRA ---
        # Se la riga ha superato i filtri, è potenzialmente il nome di un club. Puliamo le sigle.
        nome_squadra = riga_pulita
        for pattern in rimozioni_squadre:
            nome_squadra = re.sub(pattern, '', nome_squadra, flags=re.IGNORECASE)
            
        nome_squadra = nome_squadra.strip()
        
        # Verifica finale sulla lunghezza e che non si sia ridotto a solo cifre dopo la rimozione delle sigle
        if len(nome_squadra) > 2 and not nome_squadra.replace(" ", "").isdigit():
            squadre_rilevate.add(nome_squadra)
            
    return sorted(list(squadre_rilevate))

# Questo blocco simula l'input incollato dall'utente per la verifica dei filtri
if __name__ == "__main__":
    testo_copiato_da_aiscore = """[INSERIRE_TESTO_UTENTE]"""
    
    # Utilizziamo una stringa di test estratta dal palinsesto fornito
    risultato = pulisci_testo_aiscore(testo_copiato_da_aiscore)
    
    print(f"--- ESTRATTE CON SUCCESSO {len(risultato)} SQUADRE PULITE ---")
    for sq in resultado:
        print(f"-> {sq}")
