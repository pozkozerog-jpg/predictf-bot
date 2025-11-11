import requests
import os
from datetime import datetime, timedelta
import pytz
from functools import lru_cache
import hashlib

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

# In-memory кэш для inline режима (время жизни ~5 минут)
_inline_cache = {}
_cache_ttl = 300  # 5 минут в секундах

def _get_cache_key(prefix, *args):
    """Генерирует ключ кэша из префикса и аргументов"""
    key_str = f"{prefix}:{':'.join(map(str, args))}"
    return hashlib.md5(key_str.encode()).hexdigest()

def _get_cached(key):
    """Получает значение из кэша если оно свежее"""
    if key in _inline_cache:
        data, timestamp = _inline_cache[key]
        if datetime.now().timestamp() - timestamp < _cache_ttl:
            return data
        else:
            del _inline_cache[key]
    return None

def _set_cached(key, value):
    """Сохраняет значение в кэш с текущим временем"""
    _inline_cache[key] = (value, datetime.now().timestamp())

def _get(endpoint, params=None):
    """Helper function to make API requests"""
    url = f"{API_URL}{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[API Error] {endpoint}: {e}")
        return {}

# Топ-10 лиг + сборные + еврокубки
LEAGUES = {
    "Premier League": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
    "RPL": 235,
    "Eredivisie": 88,
    "Champions League": 2,
    "Europa League": 3,
    "Conference League": 848,
    "International": 1
}

def get_match_result(match_id):
    """
    Получает результат завершенного матча
    
    Args:
        match_id: ID матча
    
    Returns:
        dict: {finished: bool, home_goals: int, away_goals: int}
    """
    data = _get("/fixtures", params={"id": match_id})
    
    if not data or "response" not in data or len(data["response"]) == 0:
        return None
    
    fixture = data["response"][0]
    status = fixture.get("fixture", {}).get("status", {}).get("short", "")
    
    # Матч завершен
    if status in ["FT", "AET", "PEN"]:
        goals = fixture.get("goals", {})
        return {
            "finished": True,
            "home_goals": goals.get("home", 0),
            "away_goals": goals.get("away", 0)
        }
    
    return {"finished": False}


def get_league_rounds(league_id, season=None):
    """Получает список раундов для лиги"""
    if not season:
        season = datetime.now().year
    
    data = _get("/fixtures/rounds", params={"league": league_id, "season": season})
    rounds = data.get("response", [])
    return rounds


def fetch_upcoming_rounds(league_id, league_name, max_rounds=5):
    """
    Получает следующие раунды для лиги на основе текущих матчей
    Возвращает список словарей: [{code, label, matches_count}, ...]
    """
    # Футбольные сезоны начинаются летом и обозначаются годом начала
    # Например, сезон 2024/2025 обозначается как 2024
    current_date = datetime.now()
    if current_date.month >= 7:  # Июль и позже - новый сезон
        season = current_date.year
    else:  # Январь-июнь - предыдущий год
        season = current_date.year - 1
    
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    end = now + timedelta(days=60)
    
    print(f"[DEBUG fetch_upcoming_rounds] league_id={league_id}, season={season}, from={now.strftime('%Y-%m-%d')}, to={end.strftime('%Y-%m-%d')}")
    
    # Получаем предстоящие матчи для текущего сезона
    data = _get("/fixtures", params={
        "league": league_id,
        "season": season,
        "from": now.strftime("%Y-%m-%d"),
        "to": end.strftime("%Y-%m-%d")
    })
    
    fixtures = data.get("response", [])
    print(f"[DEBUG fetch_upcoming_rounds] Got {len(fixtures)} fixtures from API for season {season}")
    
    # Если не нашли матчи в текущем сезоне, попробуем следующий
    if not fixtures:
        print(f"[DEBUG fetch_upcoming_rounds] Trying next season {season + 1}")
        data = _get("/fixtures", params={
            "league": league_id,
            "season": season + 1,
            "from": now.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d")
        })
        fixtures = data.get("response", [])
        print(f"[DEBUG fetch_upcoming_rounds] Got {len(fixtures)} fixtures from API for season {season + 1}")
    
    # Группируем по раундам
    rounds_dict = {}
    for fixture in fixtures:
        round_code = fixture.get("league", {}).get("round", "")
        if not round_code:
            continue
        
        if round_code not in rounds_dict:
            rounds_dict[round_code] = {
                "code": round_code,
                "label": format_round_label(round_code, league_name),
                "matches_count": 0,
                "first_match_date": None
            }
        
        rounds_dict[round_code]["matches_count"] += 1
        
        # Отслеживаем дату первого матча в раунде
        match_date_str = fixture.get("fixture", {}).get("date")
        try:
            match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
            if rounds_dict[round_code]["first_match_date"] is None or match_date < rounds_dict[round_code]["first_match_date"]:
                rounds_dict[round_code]["first_match_date"] = match_date
        except:
            pass
    
    # Сортируем по дате первого матча
    sorted_rounds = sorted(rounds_dict.values(), key=lambda x: x["first_match_date"] if x["first_match_date"] else datetime.max.replace(tzinfo=pytz.UTC))
    
    # Возвращаем первые max_rounds раундов
    return sorted_rounds[:max_rounds]


def format_round_label(round_code, league_name=""):
    """Форматирует название раунда для отображения"""
    # Убираем префиксы типа "Regular Season - "
    clean_round = round_code.replace("Regular Season - ", "")
    clean_round = clean_round.replace("Group Stage - ", "Групповой этап - ")
    
    # Переводим плейофф стадии
    playoff_stages = {
        "Round of 16": "1/8 финала",
        "Quarter-finals": "1/4 финала",
        "Semi-finals": "1/2 финала",
        "Final": "Финал",
        "3rd Place Final": "Матч за 3-е место",
        "Play-offs": "Плей-офф"
    }
    
    for eng, rus in playoff_stages.items():
        if eng in clean_round:
            clean_round = clean_round.replace(eng, rus)
    
    # Если это просто число (тур лиги)
    if clean_round.isdigit():
        return f"Тур {clean_round}"
    
    return clean_round


def get_upcoming_matches(hours_ahead=24, next_n=None, window_hours=None, league_filter=None, round_filter=None):
    """Возвращает список ближайших матчей по всем топ-лигам"""
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    
    if window_hours:
        end = now + timedelta(hours=window_hours)
    else:
        end = now + timedelta(hours=hours_ahead)

    matches = []
    
    # Определяем какие лиги загружать
    leagues_to_fetch = LEAGUES
    if league_filter:
        # league_filter может содержать ID лиг (числа) или названия лиг (строки)
        leagues_to_fetch = {k: v for k, v in LEAGUES.items() if v in league_filter or k in league_filter}

    for league_name, league_id in leagues_to_fetch.items():
        url = f"{API_URL}/fixtures"
        params = {
            "league": league_id,
            "season": datetime.now().year,
            "from": now.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d")
        }

        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=15)
            response.raise_for_status()
            data = response.json().get("response", [])
        except Exception as e:
            print(f"[Ошибка API] {league_name}: {e}")
            continue

        for match in data:
            fixture = match.get("fixture", {})
            teams = match.get("teams", {})
            league_info = match.get("league", {})
            round_code = league_info.get("round", "")
            
            # Фильтруем по раунду если указан
            if round_filter and round_code != round_filter:
                continue
            
            match_date_str = fixture.get("date")
            try:
                match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                if not match_date.tzinfo:
                    match_date = match_date.replace(tzinfo=pytz.UTC)
            except:
                match_date = now
            
            matches.append({
                "id": fixture.get("id"),
                "league": league_name,
                "round": round_code,
                "date": match_date_str,
                "kick_off": match_date,
                "home": teams.get("home", {}).get("name"),
                "home_id": teams.get("home", {}).get("id"),
                "away": teams.get("away", {}).get("name"),
                "away_id": teams.get("away", {}).get("id")
            })

    if next_n:
        matches = matches[:next_n]
    
    return matches


def get_match_data(fixture_id):
    """Возвращает расширенные данные по конкретному матчу"""
    url = f"{API_URL}/fixtures?id={fixture_id}"

    try:
        fixture_resp = requests.get(url, headers=HEADERS, timeout=15).json()
        data = fixture_resp.get("response", [])[0]

        stats_url = f"{API_URL}/fixtures/statistics?fixture={fixture_id}"
        stats_resp = requests.get(stats_url, headers=HEADERS, timeout=15).json()
        stats = stats_resp.get("response", [])

        lineup_url = f"{API_URL}/fixtures/lineups?fixture={fixture_id}"
        lineup_resp = requests.get(lineup_url, headers=HEADERS, timeout=15).json()
        lineup = lineup_resp.get("response", [])

        match_data = {
            "fixture": data.get("fixture", {}),
            "league": data.get("league", {}),
            "teams": data.get("teams", {}),
            "goals": data.get("goals", {}),
            "statistics": stats,
            "lineups": lineup
        }

        return match_data

    except Exception as e:
        print(f"[Ошибка при получении данных по матчу {fixture_id}]: {e}")
        return None


def get_lineups(fixture_id):
    """Получает составы для конкретного матча"""
    try:
        data = _get("/fixtures/lineups", params={"fixture": fixture_id})
        lineups = data.get("response", [])
        
        if lineups and len(lineups) > 0:
            return {"published": True, "data": lineups}
        else:
            return {"published": False, "data": []}
    except Exception as e:
        print(f"[Ошибка при получении составов {fixture_id}]: {e}")
        return {"published": False, "data": []}


def get_team_stats(team_id, league_id=None, season=None):
    """Получает статистику команды"""
    if season is None:
        season = datetime.now().year
    
    try:
        params = {
            "team": team_id,
            "season": season
        }
        if league_id:
            params["league"] = league_id
        
        data = _get("/teams/statistics", params=params)
        return data.get("response", {})
    except Exception as e:
        print(f"[Ошибка при получении статистики команды {team_id}]: {e}")
        return {}


def get_injuries(fixture_id=None, team_id=None, season=None):
    """
    Получает информацию о травмах и дисквалификациях
    
    Args:
        fixture_id: ID матча (опционально)
        team_id: ID команды (опционально)
        season: Сезон (опционально, по умолчанию текущий год)
    
    Returns:
        dict: Данные о травмированных и дисквалифицированных игроках
    """
    if season is None:
        season = datetime.now().year
    
    try:
        params = {"season": season}
        
        if fixture_id:
            params["fixture"] = fixture_id
        elif team_id:
            params["team"] = team_id
        else:
            return {"home": [], "away": []}
        
        data = _get("/injuries", params=params)
        injuries_list = data.get("response", [])
        
        # Группируем по командам
        injuries_by_team = {}
        for injury in injuries_list:
            team_id = injury.get("team", {}).get("id")
            if team_id not in injuries_by_team:
                injuries_by_team[team_id] = []
            
            player = injury.get("player", {})
            injuries_by_team[team_id].append({
                "player_id": player.get("id"),
                "player_name": player.get("name"),
                "photo": player.get("photo"),
                "type": injury.get("player", {}).get("type", "Unknown"),  # Injury/Suspension
                "reason": injury.get("player", {}).get("reason", "Unknown")
            })
        
        return injuries_by_team
    
    except Exception as e:
        print(f"[Ошибка при получении травм]: {e}")
        return {}


def get_halftime_stats(team_id, league_id=None, season=None, last_n_matches=10):
    """
    Получает статистику голов по таймам для команды
    
    Args:
        team_id: ID команды
        league_id: ID лиги (опционально)
        season: Сезон (опционально)
        last_n_matches: Количество последних матчей для анализа
    
    Returns:
        dict: {
            "first_half": {
                "goals_scored": int,
                "goals_conceded": int,
                "avg_scored": float,
                "avg_conceded": float
            },
            "second_half": {
                "goals_scored": int,
                "goals_conceded": int,
                "avg_scored": float,
                "avg_conceded": float
            },
            "tendency": str  # "first_half", "second_half", "balanced"
        }
    """
    if season is None:
        season = datetime.now().year
    
    try:
        # Получаем последние матчи команды
        params = {
            "team": team_id,
            "season": season,
            "last": last_n_matches
        }
        if league_id:
            params["league"] = league_id
        
        data = _get("/fixtures", params=params)
        matches = data.get("response", [])
        
        first_half = {"scored": 0, "conceded": 0}
        second_half = {"scored": 0, "conceded": 0}
        matches_analyzed = 0
        
        for match in matches:
            # Проверяем что матч завершен
            if match.get("fixture", {}).get("status", {}).get("short") not in ["FT", "AET", "PEN"]:
                continue
            
            teams = match.get("teams", {})
            score = match.get("score", {})
            
            # Определяем дом/гости
            is_home = teams.get("home", {}).get("id") == team_id
            
            halftime = score.get("halftime", {})
            fulltime = score.get("fulltime", {})
            
            # Проверяем наличие всех необходимых данных
            if not halftime or not fulltime:
                continue
            if halftime.get("home") is None or halftime.get("away") is None:
                continue
            if fulltime.get("home") is None or fulltime.get("away") is None:
                continue
            
            # Считаем голы по таймам
            if is_home:
                ht_scored = halftime["home"]
                ht_conceded = halftime["away"]
                ft_scored = fulltime["home"]
                ft_conceded = fulltime["away"]
            else:
                ht_scored = halftime["away"]
                ht_conceded = halftime["home"]
                ft_scored = fulltime["away"]
                ft_conceded = fulltime["home"]
            
            # Первый тайм
            first_half["scored"] += ht_scored
            first_half["conceded"] += ht_conceded
            
            # Второй тайм
            second_half["scored"] += (ft_scored - ht_scored)
            second_half["conceded"] += (ft_conceded - ht_conceded)
            
            matches_analyzed += 1
        
        if matches_analyzed == 0:
            return {"available": False, "error": "Недостаточно данных"}
        
        # Средние значения
        avg_1h_scored = round(first_half["scored"] / matches_analyzed, 2)
        avg_1h_conceded = round(first_half["conceded"] / matches_analyzed, 2)
        avg_2h_scored = round(second_half["scored"] / matches_analyzed, 2)
        avg_2h_conceded = round(second_half["conceded"] / matches_analyzed, 2)
        
        # Определяем тенденцию
        if avg_1h_scored > avg_2h_scored * 1.3:
            tendency = "first_half"
        elif avg_2h_scored > avg_1h_scored * 1.3:
            tendency = "second_half"
        else:
            tendency = "balanced"
        
        return {
            "available": True,
            "matches_analyzed": matches_analyzed,
            "first_half": {
                "goals_scored": first_half["scored"],
                "goals_conceded": first_half["conceded"],
                "avg_scored": avg_1h_scored,
                "avg_conceded": avg_1h_conceded
            },
            "second_half": {
                "goals_scored": second_half["scored"],
                "goals_conceded": second_half["conceded"],
                "avg_scored": avg_2h_scored,
                "avg_conceded": avg_2h_conceded
            },
            "tendency": tendency,
            "total_avg_scored": round(avg_1h_scored + avg_2h_scored, 2),
            "total_avg_conceded": round(avg_1h_conceded + avg_2h_conceded, 2)
        }
    
    except Exception as e:
        print(f"[Ошибка получения статистики по таймам для команды {team_id}]: {e}")
        return {"available": False, "error": str(e)}


def analyze_playstyle(team_stats):
    """
    Анализирует стиль игры команды на основе статистики
    
    Args:
        team_stats: Статистика команды от get_team_stats() или из match statistics
    
    Returns:
        dict: {
            "possession_style": str,  # "possession", "counter", "balanced"
            "attacking_style": str,   # "aggressive", "moderate", "defensive"
            "pressing": str,          # "high", "medium", "low"
            "description": str
        }
    """
    try:
        # Извлекаем ключевые метрики
        fixtures = team_stats.get("fixtures", {})
        total_matches = fixtures.get("played", {}).get("total", 0)
        
        if total_matches == 0:
            return {"available": False, "error": "Недостаточно данных"}
        
        # Голы и результаты
        goals_for = team_stats.get("goals", {}).get("for", {})
        goals_against = team_stats.get("goals", {}).get("against", {})
        
        avg_goals_scored = goals_for.get("average", {}).get("total", 0)
        avg_goals_conceded = goals_against.get("average", {}).get("total", 0)
        
        # Примерная оценка стиля игры (без детальных статистик матчей)
        # Высокая результативность = агрессивный стиль
        if avg_goals_scored >= 2.0:
            attacking_style = "aggressive"
        elif avg_goals_scored >= 1.2:
            attacking_style = "moderate"
        else:
            attacking_style = "defensive"
        
        # Соотношение забитых и пропущенных
        if avg_goals_conceded < 1.0:
            pressing = "high"  # Хорошая защита = высокий прессинг
        elif avg_goals_conceded < 1.5:
            pressing = "medium"
        else:
            pressing = "low"
        
        # Оценка владения (упрощенная, так как нет прямых данных о possession)
        # Предполагаем на основе результатов
        if avg_goals_scored > avg_goals_conceded * 1.5:
            possession_style = "possession"
        elif avg_goals_scored < avg_goals_conceded:
            possession_style = "counter"
        else:
            possession_style = "balanced"
        
        # Описание
        styles = {
            "possession": "Контроль мяча",
            "counter": "Контратаки",
            "balanced": "Сбалансированная игра"
        }
        
        attacks = {
            "aggressive": "Агрессивная атака",
            "moderate": "Умеренная атака",
            "defensive": "Оборонительная тактика"
        }
        
        pressings = {
            "high": "Высокий прессинг",
            "medium": "Средний прессинг",
            "low": "Низкий прессинг"
        }
        
        description = f"{styles[possession_style]}, {attacks[attacking_style]}, {pressings[pressing]}"
        
        return {
            "available": True,
            "possession_style": possession_style,
            "attacking_style": attacking_style,
            "pressing": pressing,
            "description": description,
            "avg_goals_scored": round(avg_goals_scored, 2),
            "avg_goals_conceded": round(avg_goals_conceded, 2)
        }
    
    except Exception as e:
        print(f"[Ошибка анализа стиля игры]: {e}")
        return {"available": False, "error": str(e)}


def search_teams(query):
    """
    Ищет команды по частичному имени (с кэшированием для inline режима)
    
    Args:
        query: Поисковый запрос (минимум 5 символов, например: "Arsenal", "Real")
    
    Returns:
        list: Список словарей с данными команд [{id, name, country, logo}, ...]
    """
    if not query or len(query) < 5:
        return []
    
    # Нормализуем запрос для кэша
    normalized_query = query.lower().strip()
    cache_key = _get_cache_key("search_teams", normalized_query)
    
    # Проверяем кэш
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    try:
        data = _get("/teams", params={"search": query})
        teams = data.get("response", [])
        
        result = []
        for item in teams:
            team = item.get("team", {})
            venue = item.get("venue", {})
            
            team_id = team.get("id")
            team_name = team.get("name")
            country = team.get("country")
            logo = team.get("logo")
            
            if team_id and team_name:
                result.append({
                    "id": team_id,
                    "name": team_name,
                    "country": country or "Unknown",
                    "logo": logo
                })
        
        result = result[:10]
        
        # Сохраняем в кэш
        _set_cached(cache_key, result)
        
        return result
    
    except Exception as e:
        print(f"[Ошибка поиска команды '{query}']: {e}")
        return []


def get_team_matches(team_id, days_back=7, days_ahead=30):
    """
    Получает матчи команды (прошедшие и предстоящие) с кэшированием для inline режима
    
    Args:
        team_id: ID команды
        days_back: Сколько дней назад искать (по умолчанию 7)
        days_ahead: Сколько дней вперед искать (по умолчанию 30)
    
    Returns:
        list: Список матчей, отсортированных по дате
    """
    # Проверяем кэш
    cache_key = _get_cache_key("team_matches", team_id, days_back, days_ahead)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    try:
        data = _get("/fixtures", params={
            "team": team_id,
            "from": date_from,
            "to": date_to
        })
        
        fixtures = data.get("response", [])
        matches = []
        
        for fixture in fixtures:
            fixture_info = fixture.get("fixture", {})
            teams = fixture.get("teams", {})
            league_info = fixture.get("league", {})
            goals = fixture.get("goals", {})
            status = fixture_info.get("status", {})
            
            match_date_str = fixture_info.get("date")
            try:
                match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                if not match_date.tzinfo:
                    match_date = match_date.replace(tzinfo=pytz.UTC)
            except:
                match_date = now
            
            is_finished = status.get("short") in ["FT", "AET", "PEN"]
            is_upcoming = match_date > now
            
            matches.append({
                "id": fixture_info.get("id"),
                "date": match_date_str,
                "kick_off": match_date,
                "home": teams.get("home", {}).get("name"),
                "home_id": teams.get("home", {}).get("id"),
                "away": teams.get("away", {}).get("name"),
                "away_id": teams.get("away", {}).get("id"),
                "league": league_info.get("name", "Unknown"),
                "round": league_info.get("round", ""),
                "status": "finished" if is_finished else ("upcoming" if is_upcoming else "live"),
                "home_goals": goals.get("home") if is_finished else None,
                "away_goals": goals.get("away") if is_finished else None
            })
        
        matches.sort(key=lambda x: x["kick_off"])
        
        # Сохраняем в кэш
        _set_cached(cache_key, matches)
        
        return matches
    
    except Exception as e:
        print(f"[Ошибка получения матчей команды {team_id}]: {e}")
        return []
