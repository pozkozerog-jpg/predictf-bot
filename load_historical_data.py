"""
Скрипт для загрузки исторических данных матчей за 2022-2025 годы
Использует Football-Data.org API для загрузки завершенных матчей с результатами
"""
import os
import sys
import requests
import time
from datetime import datetime
from modules.database import save_historical_match, get_historical_stats

# Принудительный вывод без буферизации
def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

# API ключ
API_KEY = os.environ.get('FOOTBALL_DATA_ORG_KEY')
BASE_URL = "https://api.football-data.org/v4"

# Лиги для загрузки (по одной для текущего сезона 2025/2026)
COMPETITIONS = {
    # 2021: "Premier League",  # ✅ Загружена
    # 2014: "La Liga",  # ✅ Загружена
    # 2002: "Bundesliga",  # ✅ Загружена
    # 2019: "Serie A",  # ✅ Загружена
    2015: "Ligue 1",  # Текущая загрузка (ПОСЛЕДНЯЯ!)
}


def make_request(url):
    """Сделать запрос к API с обработкой лимитов"""
    headers = {"X-Auth-Token": API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        
        # Проверка лимита запросов
        if response.status_code == 429:
            print("⏳ Достигнут лимит API, ждем 60 секунд...")
            time.sleep(60)
            return make_request(url)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return None


def get_matches_for_season(competition_id, season_year):
    """
    Получить все завершенные матчи для лиги и сезона
    
    Args:
        competition_id (int): ID лиги
        season_year (str): Год сезона (например, "2023")
    """
    url = f"{BASE_URL}/competitions/{competition_id}/matches?season={season_year}&status=FINISHED"
    data = make_request(url)
    
    if not data:
        return []
    
    return data.get("matches", [])


def get_standings_at_matchday(competition_id, season_year, matchday):
    """
    Получить турнирную таблицу на определенный тур
    
    Args:
        competition_id (int): ID лиги
        season_year (str): Год сезона
        matchday (int): Номер тура
    """
    url = f"{BASE_URL}/competitions/{competition_id}/standings?season={season_year}&matchday={matchday}"
    data = make_request(url)
    
    if not data:
        return []
    
    standings_data = data.get("standings", [])
    if not standings_data:
        return []
    
    # Берем основную таблицу (TOTAL)
    for table in standings_data:
        if table.get("type") == "TOTAL":
            return table.get("table", [])
    
    return []


def find_team_stats(standings, team_id):
    """Найти статистику команды в турнирной таблице"""
    for team_data in standings:
        if team_data.get("team", {}).get("id") == team_id:
            return {
                "position": team_data.get("position"),
                "points": team_data.get("points"),
                "played": team_data.get("playedGames"),
                "won": team_data.get("won"),
                "draw": team_data.get("draw"),
                "lost": team_data.get("lost"),
                "goals_for": team_data.get("goalsFor"),
                "goals_against": team_data.get("goalsAgainst"),
                "form": team_data.get("form", "")
            }
    return {}


def load_matches_for_competition(competition_id, competition_name, seasons):
    """
    Загрузить матчи для одной лиги за несколько сезонов
    
    Args:
        competition_id (int): ID лиги
        competition_name (str): Название лиги
        seasons (list): Список годов сезонов (например, ["2022", "2023", "2024"])
    """
    total_loaded = 0
    
    for season in seasons:
        print(f"\n📥 Загружаем {competition_name}, сезон {season}...")
        
        # Получаем все матчи сезона
        matches = get_matches_for_season(competition_id, season)
        log(f"   Найдено {len(matches)} завершенных матчей")
        
        if not matches:
            continue
        
        # Группируем матчи по турам для оптимизации запросов таблиц
        matches_by_matchday = {}
        for match in matches:
            matchday = match.get("matchday")
            if matchday:
                if matchday not in matches_by_matchday:
                    matches_by_matchday[matchday] = []
                matches_by_matchday[matchday].append(match)
        
        # Обрабатываем каждый тур
        for matchday in sorted(matches_by_matchday.keys()):
            matchday_matches = matches_by_matchday[matchday]
            log(f"   Тур {matchday}: {len(matchday_matches)} матчей")
            
            # Получаем таблицу на этот тур (один раз для всех матчей тура)
            standings = get_standings_at_matchday(competition_id, season, matchday)
            time.sleep(6)  # Лимит API: 10 запросов/минуту
            
            # Обрабатываем каждый матч
            for match in matchday_matches:
                try:
                    # Извлекаем данные матча
                    match_id = str(match.get("id"))
                    home_team = match.get("homeTeam", {})
                    away_team = match.get("awayTeam", {})
                    score = match.get("score", {}).get("fullTime", {})
                    
                    home_team_id = home_team.get("id")
                    away_team_id = away_team.get("id")
                    
                    # Статистика команд из таблицы
                    home_stats = find_team_stats(standings, home_team_id)
                    away_stats = find_team_stats(standings, away_team_id)
                    
                    # Формируем данные для сохранения
                    match_data = {
                        "match_id": match_id,
                        "season": season,
                        "competition_id": competition_id,
                        "competition_name": competition_name,
                        "home_team_id": home_team_id,
                        "home_team": home_team.get("name"),
                        "away_team_id": away_team_id,
                        "away_team": away_team.get("name"),
                        "match_date": match.get("utcDate"),
                        "matchday": matchday,
                        "home_goals": score.get("home"),
                        "away_goals": score.get("away"),
                        "winner": match.get("score", {}).get("winner"),
                        # Статистика домашней команды
                        "home_position": home_stats.get("position"),
                        "home_points": home_stats.get("points"),
                        "home_form": home_stats.get("form"),
                        "home_goals_for": home_stats.get("goals_for"),
                        "home_goals_against": home_stats.get("goals_against"),
                        "home_played": home_stats.get("played"),
                        "home_won": home_stats.get("won"),
                        "home_draw": home_stats.get("draw"),
                        "home_lost": home_stats.get("lost"),
                        # Статистика гостевой команды
                        "away_position": away_stats.get("position"),
                        "away_points": away_stats.get("points"),
                        "away_form": away_stats.get("form"),
                        "away_goals_for": away_stats.get("goals_for"),
                        "away_goals_against": away_stats.get("goals_against"),
                        "away_played": away_stats.get("played"),
                        "away_won": away_stats.get("won"),
                        "away_draw": away_stats.get("draw"),
                        "away_lost": away_stats.get("lost"),
                        # H2H будет заполнен позже при необходимости
                        "h2h_data": None,
                        "top_scorers": None
                    }
                    
                    # Сохраняем в БД
                    save_historical_match(match_data)
                    total_loaded += 1
                    
                except Exception as e:
                    print(f"      ⚠️ Ошибка обработки матча {match.get('id')}: {e}")
                    continue
        
        log(f"✅ Сезон {season} завершен")
    
    log(f"\n🎯 Загружено {total_loaded} матчей для {competition_name}")
    return total_loaded


def main():
    """Основная функция загрузки исторических данных"""
    print("🚀 Начинаем загрузку исторических данных...")
    print(f"📊 API ключ: {'✅ Установлен' if API_KEY else '❌ Отсутствует'}")
    
    if not API_KEY:
        print("❌ Установите переменную окружения FOOTBALL_DATA_ORG_KEY")
        return
    
    # Показываем текущую статистику БД
    stats = get_historical_stats()
    print(f"\n📈 Текущая база данных:")
    print(f"   Матчей: {stats.get('total_matches', 0)}")
    print(f"   Сезонов: {stats.get('seasons_count', 0)}")
    print(f"   Лиг: {stats.get('competitions_count', 0)}")
    
    # Сезоны для загрузки (ТЕКУЩИЙ СЕЗОН 2025/2026)
    seasons = ["2025"]
    
    print(f"\n📅 Будут загружены сезоны: {', '.join(seasons)}")
    print(f"🏆 Лиг для обработки: {len(COMPETITIONS)}")
    print(f"\n✅ Начинаем загрузку...")
    
    # Загружаем данные для каждой лиги
    total_matches = 0
    start_time = time.time()
    
    for comp_id, comp_name in COMPETITIONS.items():
        try:
            loaded = load_matches_for_competition(comp_id, comp_name, seasons)
            total_matches += loaded
        except Exception as e:
            print(f"❌ Ошибка загрузки {comp_name}: {e}")
            continue
    
    # Итоговая статистика
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"🎉 ЗАГРУЗКА ЗАВЕРШЕНА!")
    print(f"{'='*60}")
    print(f"📊 Всего загружено матчей: {total_matches}")
    print(f"⏱️ Время выполнения: {elapsed/60:.1f} минут")
    
    # Обновленная статистика БД
    stats = get_historical_stats()
    print(f"\n📈 Итоговая база данных:")
    print(f"   Матчей: {stats.get('total_matches', 0)}")
    print(f"   Сезонов: {stats.get('seasons_count', 0)}")
    print(f"   Лиг: {stats.get('competitions_count', 0)}")
    
    if stats.get('seasons'):
        print(f"   Доступные сезоны: {', '.join(stats['seasons'])}")


if __name__ == "__main__":
    main()
