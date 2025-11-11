"""
Модуль для работы с SportDevs Football API (SportAPI)
Предоставляет обновляемую статистику, информацию о стадионах и игроках
"""
import requests
import os
from datetime import datetime

API_KEY = os.getenv("SPORT_API_KEY")
API_URL = "https://api.sportdevs.com/v1"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}


def _get(endpoint, params=None):
    """Helper function для запросов к SportAPI"""
    if not API_KEY:
        return {}
    
    url = f"{API_URL}{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[SportAPI Error] {endpoint}: {e}")
        return {}


def get_live_matches():
    """Получает текущие live матчи"""
    data = _get("/football/matches/live")
    return data.get("data", [])


def get_match_details(match_id):
    """Получает детальную информацию о матче"""
    data = _get(f"/football/matches/{match_id}")
    return data.get("data", {})


def get_match_statistics(match_id):
    """Получает подробную статистику матча"""
    data = _get(f"/football/matches/{match_id}/statistics")
    return data.get("data", {})


def get_team_info(team_id):
    """Получает информацию о команде"""
    data = _get(f"/football/teams/{team_id}")
    return data.get("data", {})


def get_team_squad(team_id):
    """Получает состав команды"""
    data = _get(f"/football/teams/{team_id}/squad")
    return data.get("data", {})


def get_player_info(player_id):
    """Получает информацию об игроке"""
    data = _get(f"/football/players/{player_id}")
    return data.get("data", {})


def get_player_stats(player_id, season=None):
    """Получает статистику игрока за сезон"""
    params = {}
    if season:
        params["season"] = season
    
    data = _get(f"/football/players/{player_id}/statistics", params=params)
    return data.get("data", {})


def get_stadium_info(stadium_id):
    """Получает информацию о стадионе"""
    data = _get(f"/football/stadiums/{stadium_id}")
    return data.get("data", {})


def get_venue_matches(venue_id):
    """Получает матчи на конкретном стадионе"""
    data = _get(f"/football/venues/{venue_id}/matches")
    return data.get("data", [])


def get_team_form(team_id, limit=5):
    """
    Получает форму команды (последние матчи)
    """
    data = _get(f"/football/teams/{team_id}/matches", params={"limit": limit})
    matches = data.get("data", [])
    
    form = []
    for match in matches:
        result = match.get("result", {})
        home_team = match.get("home_team", {}).get("id")
        winner = result.get("winner")
        
        if winner == team_id:
            form.append("W")
        elif winner == "draw" or winner is None:
            form.append("D")
        else:
            form.append("L")
    
    return "".join(form)


def get_team_recent_performance(team_id):
    """
    Получает расширенную статистику последних выступлений команды
    """
    matches = _get(f"/football/teams/{team_id}/matches", params={"limit": 10})
    match_data = matches.get("data", [])
    
    if not match_data:
        return {}
    
    wins = 0
    draws = 0
    losses = 0
    goals_scored = 0
    goals_conceded = 0
    clean_sheets = 0
    
    for match in match_data:
        result = match.get("result", {})
        home_team_id = match.get("home_team", {}).get("id")
        away_team_id = match.get("away_team", {}).get("id")
        home_score = result.get("home", 0)
        away_score = result.get("away", 0)
        
        is_home = home_team_id == team_id
        
        if is_home:
            team_score = home_score
            opponent_score = away_score
        else:
            team_score = away_score
            opponent_score = home_score
        
        goals_scored += team_score
        goals_conceded += opponent_score
        
        if opponent_score == 0:
            clean_sheets += 1
        
        if team_score > opponent_score:
            wins += 1
        elif team_score == opponent_score:
            draws += 1
        else:
            losses += 1
    
    return {
        "matches_played": len(match_data),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_scored": goals_scored,
        "goals_conceded": goals_conceded,
        "clean_sheets": clean_sheets,
        "avg_goals_scored": round(goals_scored / len(match_data), 2) if match_data else 0,
        "avg_goals_conceded": round(goals_conceded / len(match_data), 2) if match_data else 0,
        "form": get_team_form(team_id, 5)
    }


def enrich_with_sport_api(match_id, home_team_id, away_team_id):
    """
    Обогащает данные матча информацией из SportAPI
    """
    enriched = {
        "match_details": get_match_details(match_id) if match_id else {},
        "match_statistics": get_match_statistics(match_id) if match_id else {},
        "home_performance": get_team_recent_performance(home_team_id) if home_team_id else {},
        "away_performance": get_team_recent_performance(away_team_id) if away_team_id else {}
    }
    
    return enriched
