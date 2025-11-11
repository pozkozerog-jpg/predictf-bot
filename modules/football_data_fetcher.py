"""
Модуль для работы с Football-Data.org API
Предоставляет дополнительную статистику: турнирные таблицы, H2H, бомбардиров
"""
import requests
import os
from datetime import datetime

API_KEY = os.getenv("FOOTBALL_DATA_ORG_KEY")
API_URL = "https://api.football-data.org/v4"

HEADERS = {
    "X-Auth-Token": API_KEY
}

COMPETITION_CODES = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Ligue 1": "FL1",
    "Champions League": "CL",
    "Eredivisie": "DED",
    "Championship": "ELC",
    "Primeira Liga": "PPL",
    "Campeonato Brasileiro Série A": "BSA",
    "World Cup": "WC",
    "European Championship": "EC"
}

# Маппинг league_id -> competition code
LEAGUE_ID_TO_CODE = {
    39: "PL",      # Premier League
    140: "PD",     # La Liga
    135: "SA",     # Serie A
    78: "BL1",     # Bundesliga
    61: "FL1",     # Ligue 1
    2: "CL",       # Champions League
    88: "DED",     # Eredivisie
    235: "PPL",    # Primeira Liga (Португалия)
    40: "ELC",     # Championship (Англия, 2-я лига)
    71: "BSA",     # Serie A (Бразилия)
    1: "WC",       # FIFA World Cup
    4: "EC"        # UEFA European Championship
}


def _get(endpoint, params=None):
    """Helper function для запросов к API"""
    if not API_KEY:
        return {}
    
    url = f"{API_URL}{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[Football-Data.org Error] {endpoint}: {e}")
        return {}


def fetch_upcoming_rounds_football_data(league_id, max_rounds=5):
    """
    Получает следующие раунды для лиги из Football-Data.org API
    Возвращает список словарей: [{code, label, matches_count}, ...]
    """
    # Получаем код соревнования
    competition_code = LEAGUE_ID_TO_CODE.get(league_id)
    if not competition_code:
        print(f"[fetch_upcoming_rounds] Unknown league_id: {league_id}")
        return []
    
    print(f"[DEBUG fetch_upcoming_rounds_FD] league_id={league_id}, competition_code={competition_code}")
    
    # Получаем предстоящие матчи
    data = _get(f"/competitions/{competition_code}/matches", params={"status": "SCHEDULED"})
    
    matches = data.get("matches", [])
    print(f"[DEBUG fetch_upcoming_rounds_FD] Got {len(matches)} scheduled matches")
    
    if not matches:
        return []
    
    # Группируем по турам (matchday)
    rounds_dict = {}
    for match in matches:
        matchday = match.get("matchday")
        stage = match.get("stage", "REGULAR")
        
        if matchday is None:
            continue
        
        # Формируем код раунда
        if stage == "REGULAR_SEASON" or stage == "REGULAR":
            round_code = f"Regular Season - {matchday}"
            round_label = f"Тур {matchday}"
        elif stage == "GROUP_STAGE":
            round_code = f"Group Stage - {matchday}"
            round_label = f"Групповой этап - {matchday}"
        elif "ROUND_OF_16" in stage:
            round_code = "Round of 16"
            round_label = "1/8 финала"
        elif "QUARTER" in stage:
            round_code = "Quarter-finals"
            round_label = "1/4 финала"
        elif "SEMI" in stage:
            round_code = "Semi-finals"
            round_label = "1/2 финала"
        elif "FINAL" in stage and "THIRD" not in stage:
            round_code = "Final"
            round_label = "Финал"
        elif "THIRD" in stage:
            round_code = "3rd Place Final"
            round_label = "Матч за 3-е место"
        else:
            round_code = f"{stage} - {matchday}"
            round_label = f"{stage} - {matchday}"
        
        if round_code not in rounds_dict:
            rounds_dict[round_code] = {
                "code": round_code,
                "label": round_label,
                "matches_count": 0,
                "first_match_date": None
            }
        
        rounds_dict[round_code]["matches_count"] += 1
        
        # Отслеживаем дату первого матча
        match_date_str = match.get("utcDate")
        if match_date_str:
            try:
                match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                if rounds_dict[round_code]["first_match_date"] is None or match_date < rounds_dict[round_code]["first_match_date"]:
                    rounds_dict[round_code]["first_match_date"] = match_date
            except:
                pass
    
    # Сортируем по дате первого матча
    sorted_rounds = sorted(
        rounds_dict.values(),
        key=lambda x: x["first_match_date"] if x["first_match_date"] else datetime.max
    )
    
    print(f"[DEBUG fetch_upcoming_rounds_FD] Found {len(sorted_rounds)} rounds")
    for r in sorted_rounds[:max_rounds]:
        print(f"  - {r['label']}: {r['matches_count']} matches")
    
    # Возвращаем первые max_rounds раундов
    return sorted_rounds[:max_rounds]


def get_matches_from_football_data(league_id, round_filter=None):
    """
    Получает матчи из Football-Data.org API
    league_id - ID лиги из API-Football (39, 140 и т.д.)
    round_filter - фильтр раунда (например "Regular Season - 11")
    """
    competition_code = LEAGUE_ID_TO_CODE.get(league_id)
    if not competition_code:
        print(f"[get_matches_from_FD] Unknown league_id: {league_id}")
        return []
    
    print(f"[DEBUG get_matches_from_FD] league_id={league_id}, code={competition_code}, round_filter={round_filter}")
    
    # Получаем предстоящие матчи
    data = _get(f"/competitions/{competition_code}/matches", params={"status": "SCHEDULED"})
    matches = data.get("matches", [])
    
    print(f"[DEBUG get_matches_from_FD] Got {len(matches)} total scheduled matches")
    
    result = []
    for match in matches:
        matchday = match.get("matchday")
        stage = match.get("stage", "REGULAR")
        
        # Формируем код раунда для фильтрации
        if stage == "REGULAR_SEASON" or stage == "REGULAR":
            match_round_code = f"Regular Season - {matchday}"
        elif stage == "GROUP_STAGE":
            match_round_code = f"Group Stage - {matchday}"
        elif "ROUND_OF_16" in stage:
            match_round_code = "Round of 16"
        elif "QUARTER" in stage:
            match_round_code = "Quarter-finals"
        elif "SEMI" in stage:
            match_round_code = "Semi-finals"
        elif "FINAL" in stage and "THIRD" not in stage:
            match_round_code = "Final"
        elif "THIRD" in stage:
            match_round_code = "3rd Place Final"
        else:
            match_round_code = f"{stage} - {matchday}"
        
        # Фильтруем по раунду если указан
        if round_filter and match_round_code != round_filter:
            continue
        
        # Формируем данные матча в формате совместимом с API-Football
        home_team = match.get("homeTeam", {})
        away_team = match.get("awayTeam", {})
        competition = match.get("competition", {})
        
        result.append({
            "id": match.get("id"),
            "league": competition.get("name", "Unknown"),
            "round": match_round_code,
            "date": match.get("utcDate"),
            "kick_off": match.get("utcDate"),
            "home": home_team.get("name", ""),
            "home_id": home_team.get("id"),
            "away": away_team.get("name", ""),
            "away_id": away_team.get("id")
        })
    
    print(f"[DEBUG get_matches_from_FD] Filtered to {len(result)} matches")
    return result


def get_match_data_from_football_data(match_id):
    """
    Получает полные данные о матче из Football-Data.org API
    Возвращает данные в формате совместимом с API-Football
    """
    print(f"[DEBUG get_match_data_FD] Fetching match {match_id}")
    
    # Получаем данные матча
    data = _get(f"/matches/{match_id}")
    
    if not data or "id" not in data:
        print(f"[ERROR] Match {match_id} not found")
        return None
    
    # Преобразуем в формат совместимый с существующим кодом
    home_team = data.get("homeTeam", {})
    away_team = data.get("awayTeam", {})
    score = data.get("score", {})
    competition = data.get("competition", {})
    
    result = {
        "fixture": {
            "id": data.get("id"),
            "date": data.get("utcDate"),
            "status": {"short": data.get("status", "NS")}
        },
        "league": {
            "id": competition.get("id"),
            "name": competition.get("name", "Unknown"),
            "country": competition.get("area", {}).get("name", ""),
            "round": f"Regular Season - {data.get('matchday', 1)}"
        },
        "teams": {
            "home": {
                "id": home_team.get("id"),
                "name": home_team.get("name", ""),
                "logo": home_team.get("crest", "")
            },
            "away": {
                "id": away_team.get("id"),
                "name": away_team.get("name", ""),
                "logo": away_team.get("crest", "")
            }
        },
        "goals": {
            "home": score.get("fullTime", {}).get("home"),
            "away": score.get("fullTime", {}).get("away")
        },
        "statistics": [],  # Football-Data.org не предоставляет детальную статистику матча
        "lineups": []  # Football-Data.org не предоставляет составы
    }
    
    return result


def get_standings(competition_code, standing_type="TOTAL"):
    """
    Получает турнирную таблицу
    
    Args:
        competition_code: Код турнира (PL, PD, SA и т.д.)
        standing_type: Тип таблицы - "TOTAL", "HOME" или "AWAY"
    
    Returns:
        list: Таблица с позициями команд
    """
    data = _get(f"/competitions/{competition_code}/standings")
    
    standings = data.get("standings", [])
    for standing in standings:
        if standing.get("type") == standing_type:
            return standing.get("table", [])
    
    # Fallback на первую доступную таблицу если тип не найден
    if standings:
        return standings[0].get("table", [])
    return []


def get_top_scorers(competition_code, limit=5):
    """Получает лучших бомбардиров лиги"""
    data = _get(f"/competitions/{competition_code}/scorers", params={"limit": limit})
    
    scorers = data.get("scorers", [])
    result = []
    for scorer in scorers:
        player = scorer.get("player", {})
        team = scorer.get("team", {})
        result.append({
            "name": player.get("name"),
            "team": team.get("name"),
            "goals": scorer.get("goals", 0),
            "assists": scorer.get("assists", 0)
        })
    return result


def get_team_matches(team_id, status="FINISHED", limit=5):
    """Получает последние матчи команды"""
    data = _get(f"/teams/{team_id}/matches", params={"status": status, "limit": limit})
    
    matches = data.get("matches", [])
    return matches


def get_h2h_stats(team1_name, team2_name):
    """
    Получает статистику личных встреч (H2H)
    Примечание: требуется более высокий план API для полного H2H
    """
    try:
        data = _get("/matches")
        matches = data.get("matches", [])
        
        h2h_matches = []
        for match in matches:
            home = match.get("homeTeam", {}).get("name", "")
            away = match.get("awayTeam", {}).get("name", "")
            
            if (team1_name in home and team2_name in away) or \
               (team2_name in home and team1_name in away):
                h2h_matches.append(match)
        
        return h2h_matches[:5]
    except Exception:
        return []


def get_competition_matches(competition_code, date_filter="TODAY"):
    """Получает матчи турнира на определенную дату"""
    params = {}
    if date_filter:
        params["date"] = date_filter
    
    data = _get(f"/competitions/{competition_code}/matches", params=params)
    return data.get("matches", [])


def get_team_stats_extended(team_name, competition_code=None, venue="TOTAL"):
    """
    Расширенная статистика команды
    
    Args:
        team_name: Название команды
        competition_code: Код турнира (PL, PD и т.д.)
        venue: "TOTAL", "HOME" или "AWAY" - тип статистики
    
    Returns:
        dict: Позиция в таблице, форма, последние матчи
    """
    if not competition_code:
        return {}
    
    standings = get_standings(competition_code, standing_type=venue)
    team_stats = {}
    
    for position, team in enumerate(standings, 1):
        if team_name.lower() in team.get("team", {}).get("name", "").lower():
            team_stats = {
                "position": position,
                "points": team.get("points", 0),
                "played": team.get("playedGames", 0),
                "won": team.get("won", 0),
                "draw": team.get("draw", 0),
                "lost": team.get("lost", 0),
                "goals_for": team.get("goalsFor", 0),
                "goals_against": team.get("goalsAgainst", 0),
                "goal_difference": team.get("goalDifference", 0),
                "form": team.get("form", "")
            }
            break
    
    return team_stats


def enrich_match_data(home_team, away_team, league):
    """
    Обогащает данные матча информацией из Football-Data.org
    Получает отдельную статистику для дома и гостей с fallback на TOTAL
    """
    competition_code = COMPETITION_CODES.get(league)
    
    if not competition_code:
        return {}
    
    # Получаем раздельную статистику: хозяева - HOME stats, гости - AWAY stats
    home_stats = get_team_stats_extended(home_team, competition_code, venue="HOME")
    away_stats = get_team_stats_extended(away_team, competition_code, venue="AWAY")
    
    # Fallback: если HOME/AWAY пустая, используем TOTAL статистику
    if not home_stats or home_stats.get("played", 0) == 0:
        home_stats = get_team_stats_extended(home_team, competition_code, venue="TOTAL")
    
    if not away_stats or away_stats.get("played", 0) == 0:
        away_stats = get_team_stats_extended(away_team, competition_code, venue="TOTAL")
    
    enriched_data = {
        "home_stats": home_stats,
        "away_stats": away_stats,
        "top_scorers": get_top_scorers(competition_code, limit=3),
        "h2h": get_h2h_stats(home_team, away_team)
    }
    
    return enriched_data
