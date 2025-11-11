import requests
import os

# Odds API для получения коэффициентов легальных БК в России
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"

# Список легальных БК в России
LEGAL_BOOKMAKERS = [
    "Winline",
    "BetBoom",
    "Liga Stavok",
    "Fonbet",
    "Leon"
]

def get_odds_for_match(home_team, away_team):
    """Получение коэффициентов с Odds API для конкретного матча"""
    try:
        if not ODDS_API_KEY:
            return []
        
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal"
        }
        response = requests.get(ODDS_URL, params=params, timeout=15)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        
        if not isinstance(data, list):
            return []

        match_odds = []
        for event in data:
            if home_team.lower() in event["home_team"].lower() or away_team.lower() in event["away_team"].lower():
                for bookmaker in event["bookmakers"]:
                    name = bookmaker["title"]
                    if any(legal.lower() in name.lower() for legal in LEGAL_BOOKMAKERS):
                        outcomes = bookmaker["markets"][0]["outcomes"]
                        odds = {
                            "bookmaker": name,
                            "home": outcomes[0]["price"],
                            "draw": outcomes[1]["price"] if len(outcomes) > 2 else "-",
                            "away": outcomes[-1]["price"]
                        }
                        match_odds.append(odds)
        return match_odds[:3]  # возвращаем максимум 3 лучших БК
    except Exception as e:
        print(f"[Ошибка получения коэффициентов]: {e}")
        return []


def format_match_analysis(match_or_data, predictions_or_home_stats=None, away_stats=None, odds=None, analysis=None):
    """
    Формирует красивое сообщение о матче.
    Поддерживает два режима:
    1. format_match_analysis(match_data, predictions) - для main.py
    2. format_match_analysis(match, home_stats, away_stats, odds, analysis) - для scheduler.py
    """
    
    if analysis is not None:
        match = match_or_data
        predictions = analysis
        home_name = match.get("home", "Home")
        away_name = match.get("away", "Away")
        date = match.get("date", "Неизвестно")[:16].replace("T", " ")
        teams = predictions.get("teams", f"{home_name} vs {away_name}")
        odds_list = []
    else:
        match_data = match_or_data
        predictions = predictions_or_home_stats
        fixture = match_data.get("fixture", {})
        teams = predictions.get("teams", "")
        odds_list = get_odds_for_match(
            match_data["teams"]["home"]["name"],
            match_data["teams"]["away"]["name"]
        )
        date = fixture.get("date", "Неизвестно")[:16].replace("T", " ")

    message = f"""
🏆 <b>{teams}</b>
📅 <b>Дата:</b> {date}
"""

    # Добавляем информацию о позициях и форме (если есть)
    if predictions.get("home_position") or predictions.get("away_position"):
        message += "\n📊 <b>Позиции в таблице:</b>\n"
        if predictions.get("home_position"):
            home_team = teams.split(" vs ")[0] if " vs " in teams else "Хозяева"
            message += f"🏠 {home_team}: {predictions['home_position']}\n"
        if predictions.get("away_position"):
            away_team = teams.split(" vs ")[1] if " vs " in teams else "Гости"
            message += f"🏃 {away_team}: {predictions['away_position']}\n"
    
    # Добавляем форму команд
    if predictions.get("home_form") or predictions.get("away_form"):
        message += "\n🔥 <b>Форма (последние 5 матчей):</b>\n"
        if predictions.get("home_form"):
            home_team = teams.split(" vs ")[0] if " vs " in teams else "Хозяева"
            message += f"🏠 {home_team}: {predictions['home_form']}\n"
        if predictions.get("away_form"):
            away_team = teams.split(" vs ")[1] if " vs " in teams else "Гости"
            message += f"🏃 {away_team}: {predictions['away_form']}\n"
    
    # Анализ формы
    if predictions.get("form_analysis"):
        message += f"\n💡 {predictions['form_analysis']}\n"
    
    # Новые источники данных учитываются в прогнозе, но не показываются отдельно
    # (факторы погоды, травм, статистики тайма, стиля игры применяются внутри расчетов)

    message += f"""
📊 <b>Статистический прогноз:</b>
────────────────────────
⚽ {predictions["total_goals"]}
📐 {predictions["corners"]}
🟨 {predictions["cards"]}
🎯 {predictions["both_to_score"]}
🏅 {predictions["expected_result"]}
🏠 {predictions["home_total"]}
🏃 {predictions["away_total"]}
📈 <b>Уверенность:</b> {predictions["confidence"]}%
"""

    # H2H статистика
    if predictions.get("h2h_summary"):
        message += f"\n📈 <b>История встреч:</b> {predictions['h2h_summary']}\n"

    # Детальная статистика последних матчей (из SportAPI)
    home_perf = predictions.get("home_performance", {})
    away_perf = predictions.get("away_performance", {})
    
    if home_perf or away_perf:
        message += "\n📊 <b>Статистика последних 10 матчей:</b>\n"
        
        if home_perf:
            home_team = teams.split(" vs ")[0] if " vs " in teams else "Хозяева"
            wins = home_perf.get("wins", 0)
            draws = home_perf.get("draws", 0)
            losses = home_perf.get("losses", 0)
            goals_scored = home_perf.get("goals_scored", 0)
            goals_conceded = home_perf.get("goals_conceded", 0)
            clean_sheets = home_perf.get("clean_sheets", 0)
            
            message += f"\n🏠 <b>{home_team}:</b>\n"
            message += f"   Победы: {wins} | Ничьи: {draws} | Поражения: {losses}\n"
            message += f"   Голов забито: {goals_scored} (ср. {home_perf.get('avg_goals_scored', 0)})\n"
            message += f"   Голов пропущено: {goals_conceded} (ср. {home_perf.get('avg_goals_conceded', 0)})\n"
            message += f"   Сухих матчей: {clean_sheets} 🛡️\n"
        
        if away_perf:
            away_team = teams.split(" vs ")[1] if " vs " in teams else "Гости"
            wins = away_perf.get("wins", 0)
            draws = away_perf.get("draws", 0)
            losses = away_perf.get("losses", 0)
            goals_scored = away_perf.get("goals_scored", 0)
            goals_conceded = away_perf.get("goals_conceded", 0)
            clean_sheets = away_perf.get("clean_sheets", 0)
            
            message += f"\n🏃 <b>{away_team}:</b>\n"
            message += f"   Победы: {wins} | Ничьи: {draws} | Поражения: {losses}\n"
            message += f"   Голов забито: {goals_scored} (ср. {away_perf.get('avg_goals_scored', 0)})\n"
            message += f"   Голов пропущено: {goals_conceded} (ср. {away_perf.get('avg_goals_conceded', 0)})\n"
            message += f"   Сухих матчей: {clean_sheets} 🛡️\n"

    # Рекомендации для ставок
    betting_tips = predictions.get("betting_tips", [])
    if betting_tips:
        message += "\n────────────────────────\n💰 <b>Рекомендации для ставок:</b>\n"
        for i, tip in enumerate(betting_tips, 1):
            message += f"\n{i}. {tip}"
    
    # Value Bet рекомендации учитываются внутри расчетов, но не выводятся отдельно
    
    message += "\n\n🕒 Время по МСК"

    return message
