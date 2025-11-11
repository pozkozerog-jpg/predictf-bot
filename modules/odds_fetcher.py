"""
Попытка взять линии/коэффициенты:
- сначала пробуем API-Football /odds (если доступно),
- иначе пробуем external odds API если задан ODDS_API_KEY (пример: the-odds-api).
"""
import os
from modules.data_fetcher import _get
import requests

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
LEGAL_BOOKMAKERS = [
    "Fonbet", "Winline", "BetCity", "Pari", "Melbet", "Liga Stavok",
    "Marathon", "Tennisi", "Betboom", "Leon", "Baltbet", "Zenit",
    "Olimp", "Bettery", "Sportbet", "BET-M"
]

def get_odds_from_api_football(fixture_id):
    try:
        data = _get("/odds", params={"fixture": fixture_id})
    except Exception:
        return {}
    res = {}
    for book in data.get("response", []):
        name = book.get("bookmaker", {}).get("name")
        markets = book.get("bets", []) or []
        obj = {"1": None, "X": None, "2": None, "O2.5": None, "BTTS": None}
        for m in markets:
            label = m.get("label", "")
            for val in m.get("values", []):
                v = val.get("value")
                odd = val.get("odd")
                if "Home" in v or v == "1":
                    obj["1"] = odd
                if "Draw" in v or v == "X":
                    obj["X"] = odd
                if "Away" in v or v == "2":
                    obj["2"] = odd
                if "Over 2.5" in v:
                    obj["O2.5"] = odd
                if "Yes" in v and ("Both" in label or "Both Teams To Score" in label):
                    obj["BTTS"] = odd
        if name:
            res[name] = obj
    # ensure legal bookmakers keys exist as placeholders
    for lb in LEGAL_BOOKMAKERS:
        res.setdefault(lb, {"1": None, "X": None, "2": None, "O2.5": None, "BTTS": None})
    return res

def get_odds_from_external():
    # Example: the-odds-api
    try:
        if not ODDS_API_KEY:
            return {}
        url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?regions=eu&markets=h2h,totals&oddsFormat=decimal&apiKey={ODDS_API_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        # map some data (simplified)
        out = {}
        for item in data[:10]:
            try:
                bk = item["bookmakers"][0]["title"]
                market = item["bookmakers"][0]["markets"][0]
                # store first outcomes
                out[bk] = {"raw": market}
            except Exception:
                continue
        return out
    except Exception:
        return {}

def fetch_odds(fixture_id):
    """Главная функция: возвращает объединённую таблицу коэффициентов."""
    res = get_odds_from_api_football(fixture_id)
    if not res or all(v["1"] is None and v["X"] is None and v["2"] is None for v in res.values()):
        # fallback to external
        res = get_odds_from_external()
    return res


def decimal_to_probability(decimal_odds):
    """
    Конвертирует десятичные коэффициенты в вероятность (%)
    
    Args:
        decimal_odds: Десятичный коэффициент (например, 2.50)
    
    Returns:
        float: Вероятность в процентах (например, 40.0)
    """
    if not decimal_odds or decimal_odds <= 1.0:
        return 0.0
    
    try:
        probability = (1 / float(decimal_odds)) * 100
        return round(probability, 2)
    except (ValueError, ZeroDivisionError):
        return 0.0


def find_best_odds(odds_data, market="1X2"):
    """
    Находит лучшие коэффициенты среди всех букмекеров
    
    Args:
        odds_data: Данные о коэффициентах от fetch_odds()
        market: Тип ставки ("1X2" для победителя, "O2.5" для тотала, "BTTS" для обе забьют)
    
    Returns:
        dict: {
            "home_win": {"odds": float, "bookmaker": str, "probability": float},
            "draw": {"odds": float, "bookmaker": str, "probability": float},
            "away_win": {"odds": float, "bookmaker": str, "probability": float}
        }
    """
    best_odds = {
        "home_win": {"odds": None, "bookmaker": None, "probability": 0},
        "draw": {"odds": None, "bookmaker": None, "probability": 0},
        "away_win": {"odds": None, "bookmaker": None, "probability": 0}
    }
    
    for bookmaker, markets in odds_data.items():
        if not isinstance(markets, dict):
            continue
        
        # П1 (Home Win)
        home_odds = markets.get("1")
        if home_odds and (best_odds["home_win"]["odds"] is None or float(home_odds) > float(best_odds["home_win"]["odds"])):
            best_odds["home_win"] = {
                "odds": float(home_odds),
                "bookmaker": bookmaker,
                "probability": decimal_to_probability(float(home_odds))
            }
        
        # Ничья (Draw)
        draw_odds = markets.get("X")
        if draw_odds and (best_odds["draw"]["odds"] is None or float(draw_odds) > float(best_odds["draw"]["odds"])):
            best_odds["draw"] = {
                "odds": float(draw_odds),
                "bookmaker": bookmaker,
                "probability": decimal_to_probability(float(draw_odds))
            }
        
        # П2 (Away Win)
        away_odds = markets.get("2")
        if away_odds and (best_odds["away_win"]["odds"] is None or float(away_odds) > float(best_odds["away_win"]["odds"])):
            best_odds["away_win"] = {
                "odds": float(away_odds),
                "bookmaker": bookmaker,
                "probability": decimal_to_probability(float(away_odds))
            }
    
    return best_odds


def analyze_value_bets(bot_predictions, odds_data, min_edge=5.0):
    """
    Анализирует value bet - сравнивает вероятности бота с букмекерскими коэффициентами
    
    Value bet = когда бот дает более высокую вероятность чем букмекер
    Например: Бот 55% на победу, букмекер 2.00 (50%) → Value bet +5%
    
    Args:
        bot_predictions: Прогнозы бота с вероятностями {
            "home_win": 0.45,  # 45%
            "draw": 0.25,      # 25%
            "away_win": 0.30   # 30%
        }
        odds_data: Данные о коэффициентах от fetch_odds()
        min_edge: Минимальное преимущество для value bet (по умолчанию 5%)
    
    Returns:
        dict: {
            "has_value": bool,
            "value_bets": [
                {
                    "outcome": "home_win",
                    "bot_probability": 45.0,
                    "bookmaker_probability": 40.0,
                    "edge": 5.0,
                    "best_odds": 2.50,
                    "bookmaker": "Fonbet",
                    "recommendation": "Value bet на П1"
                }
            ]
        }
    """
    best_odds = find_best_odds(odds_data)
    value_bets = []
    
    outcomes = {
        "home_win": "П1 (Победа хозяев)",
        "draw": "Ничья",
        "away_win": "П2 (Победа гостей)"
    }
    
    for outcome_key, outcome_name in outcomes.items():
        bot_prob = bot_predictions.get(outcome_key, 0) * 100  # Конвертируем в проценты
        odds_info = best_odds.get(outcome_key, {})
        
        if not odds_info.get("odds"):
            continue
        
        bookmaker_prob = odds_info.get("probability", 0)
        edge = bot_prob - bookmaker_prob
        
        # Если есть преимущество больше минимального
        if edge >= min_edge:
            value_bets.append({
                "outcome": outcome_key,
                "outcome_name": outcome_name,
                "bot_probability": round(bot_prob, 1),
                "bookmaker_probability": round(bookmaker_prob, 1),
                "edge": round(edge, 1),
                "best_odds": odds_info["odds"],
                "bookmaker": odds_info["bookmaker"],
                "recommendation": f"💎 Value bet на {outcome_name}",
                "explanation": f"Бот: {round(bot_prob, 1)}% vs Букмекер: {round(bookmaker_prob, 1)}% (преимущество +{round(edge, 1)}%)"
            })
    
    return {
        "has_value": len(value_bets) > 0,
        "value_bets": sorted(value_bets, key=lambda x: x["edge"], reverse=True),  # Сортируем по преимуществу
        "best_available_odds": best_odds
    }
