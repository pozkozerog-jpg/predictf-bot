"""
ML модуль для самообучения бота на основе реальных результатов
Использует ТОЛЬКО локальную ML модель (scikit-learn) - БЕЗ OpenAI
"""
import os
from modules.database import get_connection, get_ml_weights, update_ml_weights
from modules.data_fetcher import get_match_result
from modules.local_ml_model import predict_weights, get_model_info, train_model
import json


def update_actual_results():
    """
    Обновляет реальные результаты завершенных матчей через API
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Получаем прогнозы без реальных результатов
    cur.execute("""
        SELECT id, match_id, home_team, away_team, 
               predicted_result, predicted_total,
               predicted_home_goals, predicted_away_goals
        FROM predictions
        WHERE actual_result IS NULL 
        AND match_date < NOW()
        LIMIT 50
    """)
    
    predictions = cur.fetchall()
    updated_count = 0
    
    for pred in predictions:
        pred_id, match_id, home_team, away_team, predicted_result, predicted_total, pred_home, pred_away = pred
        
        try:
            # Получаем реальный результат через API
            result = get_match_result(match_id)
            
            if result and result.get("finished"):
                home_goals = result.get("home_goals", 0)
                away_goals = result.get("away_goals", 0)
                actual_total = home_goals + away_goals
                
                # Определяем реальный результат
                if home_goals > away_goals:
                    actual_result = f"Победа {home_team}"
                elif away_goals > home_goals:
                    actual_result = f"Победа {away_team}"
                else:
                    actual_result = "Ничья"
                
                # Проверяем правильность прогноза
                result_correct = (predicted_result == actual_result)
                total_error = abs(predicted_total - actual_total)
                
                # Обновляем запись
                cur.execute("""
                    UPDATE predictions
                    SET actual_result = %s,
                        actual_home_goals = %s,
                        actual_away_goals = %s,
                        actual_total = %s,
                        result_correct = %s,
                        total_error = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (actual_result, home_goals, away_goals, actual_total, 
                      result_correct, total_error, pred_id))
                
                updated_count += 1
        except Exception as e:
            print(f"⚠️ Ошибка получения результата для матча {match_id}: {e}")
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Обновлено результатов: {updated_count}")
    return updated_count


def simple_weight_adjustment(predictions):
    """
    Простая эвристика для корректировки весов без AI
    Основана на анализе точности по факторам
    """
    correct_predictions = [p for p in predictions if p[16]]  # result_correct (индекс 16 с учетом новых колонок)
    incorrect_predictions = [p for p in predictions if not p[16]]
    
    accuracy = len(correct_predictions) / len(predictions)
    
    current_weights = get_ml_weights()
    new_weights = current_weights.copy()
    
    # Список всех весов для корректировки (включая form и position)
    weight_keys = ['h2h_weight', 'motivation_weight', 'streak_weight', 'form_weight', 'position_weight',
                   'weather_weight', 'injuries_weight', 'halftime_weight', 'playstyle_weight']
    
    # Если точность низкая (<60%), снижаем все веса
    if accuracy < 0.6:
        for key in weight_keys:
            new_weights[key] = max(0.5, current_weights.get(key, 1.0) * 0.9)
        print(f"📉 Точность {accuracy*100:.1f}% - снижаем веса факторов")
    # Если точность высокая (>75%), немного увеличиваем
    elif accuracy > 0.75:
        for key in weight_keys:
            new_weights[key] = min(1.5, current_weights.get(key, 1.0) * 1.05)
        print(f"📈 Точность {accuracy*100:.1f}% - увеличиваем веса факторов")
    else:
        print(f"✅ Точность {accuracy*100:.1f}% - веса остаются без изменений")
        return None
    
    return new_weights


def analyze_prediction_patterns():
    """
    Анализирует паттерны в прогнозах с помощью AI
    Определяет, какие факторы работают лучше
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Получаем последние 100 прогнозов с результатами (включая новые факторы)
    cur.execute("""
        SELECT 
            home_team, away_team,
            h2h_factor_home, h2h_factor_away,
            home_motivation, away_motivation,
            home_streak_factor, away_streak_factor,
            weather_adjustment, injuries_home_count, injuries_away_count,
            halftime_adjustment, playstyle_adjustment_home, playstyle_adjustment_away,
            predicted_result, actual_result,
            result_correct, total_error
        FROM predictions
        WHERE actual_result IS NOT NULL
        ORDER BY match_date DESC
        LIMIT 100
    """)
    
    predictions = cur.fetchall()
    cur.close()
    conn.close()
    
    if len(predictions) < 5:
        print("⚠️ Недостаточно данных для ML анализа (нужно минимум 5 матчей)")
        return None
    
    # 🤖 ЛОКАЛЬНАЯ ML МОДЕЛЬ (единственный вариант)
    print("🤖 Используем локальную ML модель для анализа...")
    model_info = get_model_info()
    
    # Проверяем нужно ли переобучить модель
    current_training_size = model_info.get('training_size', 0) if model_info.get('exists') else 0
    
    # Получаем количество исторических матчей
    conn_check = get_connection()
    cur_check = conn_check.cursor()
    cur_check.execute("SELECT COUNT(*) FROM historical_matches")
    result = cur_check.fetchone()
    total_historical = result[0] if result else 0
    cur_check.close()
    conn_check.close()
    
    # Переобучаем модель если:
    # 1. Модель не обучена ИЛИ
    # 2. Появилось много новых данных (>50 матчей с момента обучения)
    should_retrain = (
        not model_info.get('exists') or 
        (total_historical - current_training_size) > 50
    )
    
    if should_retrain:
        print(f"🔄 Переобучение модели... (исторических данных: {total_historical})")
        train_result = train_model()
        if train_result.get('success'):
            print(f"✅ Модель обучена на {train_result['training_size']} примерах")
        else:
            print(f"❌ Ошибка переобучения: {train_result.get('error')}")
            # Fallback на базовую эвристику
            return simple_weight_adjustment(predictions)
    
    # Используем модель для предсказания весов
    # На основе статистики ПРАВИЛЬНЫХ прогнозов
    correct_predictions = [p for p in predictions if p[16]]  # result_correct
    
    if not correct_predictions:
        print("⚠️ Нет правильных прогнозов для анализа")
        return simple_weight_adjustment(predictions)
    
    # ИСПРАВЛЕНО: Вычисляем РЕАЛЬНЫЕ средние признаки из прогнозов
    # Получаем агрегированные данные из БД
    conn_features = get_connection()
    cur_features = conn_features.cursor()
    
    # Берём среднюю статистику из последних 50 матчей
    cur_features.execute("""
        SELECT 
            AVG(ABS(COALESCE(home_position, 10) - COALESCE(away_position, 10))) as position_diff,
            AVG(COALESCE(home_position, 10)) as home_position,
            AVG(COALESCE(away_position, 10)) as away_position
        FROM (
            SELECT * FROM predictions 
            WHERE actual_result IS NOT NULL 
            ORDER BY match_date DESC 
            LIMIT 50
        ) recent
    """)
    avg_stats = cur_features.fetchone()
    cur_features.close()
    conn_features.close()
    
    # Используем реальные средние значения или дефолтные
    match_features = {
        'position_diff': int(avg_stats[0]) if avg_stats and avg_stats[0] else 5,
        'home_position': int(avg_stats[1]) if avg_stats and avg_stats[1] else 7,
        'away_position': int(avg_stats[2]) if avg_stats and avg_stats[2] else 12,
        # Остальные признаки - примерные средние для топ-лиг
        'home_goals_for': 45,
        'home_goals_against': 35,
        'away_goals_for': 40,
        'away_goals_against': 42,
        'home_form_wins': 2,
        'away_form_wins': 2,
        'home_goal_diff': 10,
        'away_goal_diff': -2,
        'home_points': 35,
        'away_points': 28,
        'points_diff': 7
    }
    
    local_weights = predict_weights(match_features)
    
    if local_weights:
        print(f"🎯 Локальная ML модель: {local_weights}")
        # Дополняем веса базовыми значениями для остальных факторов
        full_weights = {
            'h2h_weight': local_weights.get('h2h_weight', 1.0),
            'motivation_weight': local_weights.get('motivation_weight', 1.0),
            'streak_weight': local_weights.get('streak_weight', 1.0),
            'form_weight': 1.0,
            'position_weight': 1.0,
            'weather_weight': 1.0,
            'injuries_weight': 1.0,
            'halftime_weight': 1.0,
            'playstyle_weight': 1.0
        }
        return full_weights
    else:
        print("⚠️ Локальная модель не дала результат - используем эвристику")
        return simple_weight_adjustment(predictions)

def run_training_cycle():
    """
    Полный цикл обучения модели:
    1. Обновить реальные результаты
    2. Проанализировать паттерны с AI
    3. Обновить веса
    """
    print("🤖 Начинаю обучение ML модели...")
    
    # Шаг 1: Обновить результаты
    updated = update_actual_results()
    
    if updated > 0:
        print(f"✅ Обновлено {updated} результатов")
    else:
        print("ℹ️ Нет новых результатов, но продолжаю анализ имеющихся данных")
    
    # Шаг 2: Анализ с AI (запускается всегда, если есть исторические данные)
    new_weights = analyze_prediction_patterns()
    
    if new_weights:
        # Шаг 3: Обновить веса
        current_weights = get_ml_weights()
        
        # Плавное обновление (70% старые веса + 30% новые)
        smoothed_weights = {}
        for key in new_weights:
            old_value = current_weights.get(key, 1.0)
            new_value = new_weights[key]
            smoothed_weights[key] = old_value * 0.7 + new_value * 0.3
        
        update_ml_weights(smoothed_weights)
        print(f"✅ Веса обновлены: {smoothed_weights}")
        return True
    
    return False


if __name__ == "__main__":
    # Тестовый запуск
    run_training_cycle()
