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
