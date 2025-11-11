"""
Модуль для проверки и обновления результатов завершенных матчей
"""
import os
import requests
from modules.database import get_unverified_predictions, update_match_result

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_BASE_URL = "https://v3.football.api-sports.io"


def verify_match_results():
    """
    Проверяет результаты всех непроверенных матчей
    
    Returns:
        dict: Статистика обновлений
    """
    predictions = get_unverified_predictions(limit=50)
    
    if not predictions:
        print("Нет непроверенных матчей")
        return {"total": 0, "updated": 0, "failed": 0}
    
    print(f"Найдено {len(predictions)} непроверенных матчей")
    
    updated = 0
    failed = 0
    
    for pred in predictions:
        try:
            match_id = pred['match_id']
            
            # Получаем результат матча через API
            headers = {
                'x-apisports-key': API_KEY
            }
            
            response = requests.get(
                f"{API_BASE_URL}/fixtures",
                headers=headers,
                params={"id": match_id},
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"Ошибка API для матча {match_id}: {response.status_code}")
                failed += 1
                continue
            
            data = response.json()
            
            if not data.get('response'):
                print(f"Нет данных для матча {match_id}")
                failed += 1
                continue
            
            match = data['response'][0]
            fixture = match.get('fixture', {})
            status = fixture.get('status', {}).get('short', '')
            
            # Проверяем что матч завершен
            if status not in ['FT', 'AET', 'PEN']:
                print(f"Матч {match_id} еще не завершен (статус: {status})")
                continue
            
            # Получаем счет
            goals = match.get('goals', {})
            home_goals = goals.get('home')
            away_goals = goals.get('away')
            
            if home_goals is None or away_goals is None:
                print(f"Нет счета для матча {match_id}")
                failed += 1
                continue
            
            # Обновляем результат в базе
            success = update_match_result(
                prediction_id=pred['id'],
                home_team=pred['home_team'],
                away_team=pred['away_team'],
                actual_home_goals=home_goals,
                actual_away_goals=away_goals,
                predicted_result=pred['predicted_result']
            )
            
            if success:
                print(f"✅ Обновлен результат: {pred['home_team']} {home_goals}:{away_goals} {pred['away_team']}")
                updated += 1
            else:
                failed += 1
                
        except Exception as e:
            print(f"Ошибка обработки матча {pred.get('match_id')}: {e}")
            failed += 1
    
    print(f"\n📊 Результаты проверки:")
    print(f"  Всего: {len(predictions)}")
    print(f"  Обновлено: {updated}")
    print(f"  Ошибок: {failed}")
    
    return {
        "total": len(predictions),
        "updated": updated,
        "failed": failed
    }
