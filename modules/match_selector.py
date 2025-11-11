"""
Модуль для выбора самых интересных матчей дня
"""

from datetime import datetime, timedelta
from modules.data_fetcher import get_upcoming_matches, LEAGUES
from modules.predictor import analyze_streak

# Топ-5 лиг Европы (высший приоритет)
TOP_5_LEAGUES = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]

# Европейские турниры
EUROPEAN_COMPETITIONS = ["Champions League", "Europa League"]


def calculate_match_interest_score(match_data, league_name):
    """
    Рассчитывает балл интересности матча (0-100)
    
    Критерии:
    - Класс лиги (топ-5 = +30, еврокубки = +25, остальные = +10)
    - Известные топ-клубы (+20)
    - Дерби и принципиальные соперники (+25)
    """
    score = 0
    
    home_team = match_data.get("home", "")
    away_team = match_data.get("away", "")
    
    # 1. Класс лиги
    if league_name in TOP_5_LEAGUES:
        score += 30
    elif league_name in EUROPEAN_COMPETITIONS:
        score += 25
    else:
        score += 10
    
    # 2. Известные топ-клубы
    top_clubs = [
        "Manchester City", "Manchester United", "Liverpool", "Arsenal", "Chelsea", "Tottenham",
        "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla",
        "Bayern Munich", "Borussia Dortmund", "RB Leipzig",
        "Inter", "Milan", "Juventus", "Napoli", "Roma",
        "PSG", "Monaco", "Lyon", "Marseille"
    ]
    
    home_is_top = any(club in home_team for club in top_clubs)
    away_is_top = any(club in away_team for club in top_clubs)
    
    if home_is_top and away_is_top:
        score += 20  # Оба топ-клуба
    elif home_is_top or away_is_top:
        score += 10  # Один топ-клуб
    
    # 3. Дерби и принципиальные соперники (по названию)
    derbies = [
        ("Manchester City", "Manchester United"),
        ("Arsenal", "Tottenham"),
        ("Liverpool", "Everton"),
        ("Chelsea", "Arsenal"),
        ("Real Madrid", "Barcelona"),
        ("Real Madrid", "Atletico Madrid"),
        ("Inter", "Milan"),
        ("Juventus", "Inter"),
        ("Roma", "Lazio"),
        ("Bayern Munich", "Borussia Dortmund"),
        ("PSG", "Marseille"),
        ("Benfica", "Porto"),
        ("Ajax", "Feyenoord"),
        ("Galatasaray", "Fenerbahce"),
        ("Celtic", "Rangers"),
        ("Flamengo", "Corinthians")
    ]
    
    for team1, team2 in derbies:
        if (team1 in home_team and team2 in away_team) or \
           (team2 in home_team and team1 in away_team):
            score += 25
            break
    
    return min(score, 100)  # Максимум 100 баллов


def get_top_matches(limit=5):
    """
    Возвращает топ-N самых интересных матчей на сегодня/завтра
    
    Returns:
        list: Список словарей с данными матчей, отсортированных по интересности
              [{"match": {...}, "league_name": str, "league_id": int, "score": int, "date": date}, ...]
    """
    all_matches = []
    
    # Получаем все матчи на следующие 48 часов
    try:
        matches = get_upcoming_matches(hours_ahead=48)
        
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        for match in matches:
            match_date_str = match.get("date", "")
            league_name = match.get("league", "")
            round_code = match.get("round", "")
            
            if not match_date_str or not league_name:
                continue
            
            # Получаем league_id из словаря LEAGUES
            league_id = LEAGUES.get(league_name)
            if not league_id:
                continue
            
            try:
                match_date = datetime.fromisoformat(match_date_str.replace("Z", "+00:00")).date()
                
                # Только матчи на сегодня или завтра
                if match_date == today or match_date == tomorrow:
                    score = calculate_match_interest_score(match, league_name)
                    
                    all_matches.append({
                        "match": match,
                        "league_name": league_name,
                        "league_id": league_id,
                        "round_code": round_code,
                        "score": score,
                        "date": match_date
                    })
            
            except Exception as e:
                continue
    
    except Exception as e:
        print(f"[Ошибка получения матчей]: {e}")
        return []
    
    # Сортируем по баллам (больше = интереснее)
    all_matches.sort(key=lambda x: x["score"], reverse=True)
    
    # Возвращаем топ-N
    return all_matches[:limit]


def format_top_matches_message(top_matches):
    """
    Форматирует сообщение с топ-матчами
    
    Args:
        top_matches: Список словарей с данными матчей
    
    Returns:
        str: Отформатированное сообщение
    """
    if not top_matches:
        return "⚠️ Нет интересных матчей на сегодня/завтра"
    
    message = "⭐ *Топ-матчи дня*\n\n"
    message += "Самые интересные противостояния на основе:\n"
    message += "• Класс лиги и команд\n"
    message += "• Позиция в таблице\n"
    message += "• Форма и мотивация\n"
    message += "• История противостояний\n\n"
    
    for i, item in enumerate(top_matches, 1):
        match = item["match"]
        league_name = item["league_name"]
        score = item["score"]
        date = item["date"]
        
        home = match.get("home", "???")
        away = match.get("away", "???")
        time = match.get("time", "??:??")
        
        # Эмодзи в зависимости от балла
        if score >= 80:
            emoji = "🔥"
        elif score >= 60:
            emoji = "⚡"
        else:
            emoji = "⭐"
        
        date_str = "Сегодня" if date == datetime.now().date() else "Завтра"
        
        message += f"{emoji} *{i}. {home} vs {away}*\n"
        message += f"   {league_name} • {date_str} {time}\n"
        message += f"   Интерес: {score}/100\n\n"
    
    message += "Нажмите на матч для детального анализа! 🎯"
    
    return message
