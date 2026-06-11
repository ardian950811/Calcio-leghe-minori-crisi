import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import time

def search_team_crisis_news(team_name, country_context="global"):
    print(f"Scanning critical news for: {team_name} ({country_context})...")
    
    # Define keywords based on the language/country context
    keywords_dict = {
        "spanish": ['huelga', 'sueldos', 'deuda', 'lesion', 'crisis', 'problema', 'no entrena'],
        "french": ['grève', 'salaire', 'impayé', 'dette', 'blessure', 'crise', 'boycott'],
        "english": ['strike', 'salary', 'unpaid', 'debt', 'injury', 'crisis', 'boycott', 'protest'],
        "global": ['strike', 'salary', 'unpaid', 'injury', 'huelga', 'sueldos', 'grève']
    }
    
    # Pick the right keywords array
    keywords = keywords_dict.get(country_context.lower(), keywords_dict["global"])
    
    # Build a combined search query: "Team Name" AND (keyword1 OR keyword2 OR ...)
    keywords_query = " OR ".join([f'"{kw}"' for kw in keywords])
    full_query = f'"{team_name}" ({keywords_query})'
    
    # Encode the query for a URL
    encoded_query = urllib.parse.quote(full_query)
    
    # Google News RSS URL
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    alerts_found = []
    
    try:
        response = requests.get(rss_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, features="xml") # Using xml parser for RSS
        
        items = soup.find_all('item')
        print(f"Found {len(items)} raw search results in Google News RSS.")
        
        for item in items[:5]: # Take the top 5 most recent relevant news
            title = item.title.text
            link = item.link.text
            pub_date = item.pubDate.text
            
            alerts_found.append({
                "title": title,
                "link": link,
                "date": pub_date
            })
            
    except Exception as e:
        print(f"Error searching news for {team_name}: {e}")
        
    return alerts_found

def main_investigation():
    # TEST LIST: Put the teams you want to check manually here
    teams_to_search = [
        {"name": "Chacarita Juniors", "context": "spanish"},
        {"name": "Gor Mahia", "context": "english"},
        {"name": "USM Alger", "context": "french"}
    ]
    
    report_results = {}
    
    for team in teams_to_search:
        name = team["name"]
        context = team["context"]
        
        critical_news = search_team_crisis_news(name, context)
        report_results[name] = critical_news
        time.sleep(2) # Polite delay between requests
        
    # Save the findings to a JSON file for the web dashboard
    with open("crisis_report.json", "w", encoding="utf-8") as f:
        json.dump(report_results, f, indent=4)
        
    print("Investigation completed. 'crisis_report.json' has been updated.")

if __name__ == "__main__":
    main_investigation()
