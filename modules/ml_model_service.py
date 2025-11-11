"""
ML Model Service - загрузка и использование многомодельной системы

Этот модуль обеспечивает интеграцию 15 специализированных ML моделей
(5 лиг × 3 алгоритма) с системой прогнозов.
"""

import os
import joblib
import numpy as np
from modules.database import get_best_model_for_league

# Путь к сохраненным моделям
MODEL_PATH = "ml_models/"

# Кэш загруженных моделей для оптимизации
_model_cache = {}


def ensure_model_dir():
    """Убедиться что директория для моделей существует"""
    os.makedirs(MODEL_PATH, exist_ok=True)


def load_active_model(league):
    """
    Загрузить активную модель для лиги
    
    Args:
        league (str): Название лиги (например, "Premier League")
        
    Returns:
        dict: {
            'models': {...},  # Словарь моделей для каждого веса
            'feature_names': [...],  # Порядок признаков
            'algorithm': '...',  # Название алгоритма
            'metrics': {...}  # Метрики точности
        } или None если модель не найдена
    """
    # Проверяем кэш
    if league in _model_cache:
        return _model_cache[league]
    
    try:
        # Получаем информацию о лучшей модели из БД
        model_info = get_best_model_for_league(league)
        
        if not model_info:
            print(f"⚠️ Нет активной модели для {league}")
            return None
        
        algorithm = model_info['algorithm']
        
        # Формируем путь к файлу
        model_filename = f"{MODEL_PATH}{league.replace(' ', '_')}_{algorithm}.pkl"
        
        if not os.path.exists(model_filename):
            print(f"⚠️ Файл модели не найден: {model_filename}")
            return None
        
        # Загружаем модель
        model_data = joblib.load(model_filename)
        model_data['algorithm'] = algorithm
        
        # Кэшируем
        _model_cache[league] = model_data
        
        print(f"✅ Загружена модель: {league} / {algorithm}")
        return model_data
        
    except Exception as e:
        print(f"❌ Ошибка загрузки модели для {league}: {e}")
        return None


def predict_weights_for_match(league, match_features):
    """
    Предсказать оптимальные веса для матча используя специализированную модель лиги
    
    Args:
        league (str): Название лиги
        match_features (dict): Признаки матча:
            - position_diff: разница в позициях
            - home_position: позиция хозяев
            - away_position: позиция гостей
            - home_goals_for: забитые голы хозяев
            - home_goals_against: пропущенные голы хозяев
            - away_goals_for: забитые голы гостей
            - away_goals_against: пропущенные голы гостей
            - home_form_wins: победы в форме хозяев
            - away_form_wins: победы в форме гостей
            - home_goal_diff: разница голов хозяев
            - away_goal_diff: разница голов гостей
            - home_points: очки хозяев
            - away_points: очки гостей
            - points_diff: разница очков
            - home_win_ratio: соотношение побед хозяев
            - away_win_ratio: соотношение побед гостей
            
    Returns:
        dict: {
            'h2h_weight': float,  # Вес для H2H фактора (0.7-1.5)
            'motivation_weight': float,  # Вес для мотивации (0.7-1.5)
            'streak_weight': float,  # Вес для серии (0.7-1.5)
            'algorithm': str  # Используемый алгоритм
        } или None при ошибке
    """
    # Пытаемся загрузить модель
    model_data = load_active_model(league)
    
    if not model_data:
        print(f"⚠️ Используем дефолтные веса для {league} (модель не найдена)")
        return None
    
    try:
        models = model_data['models']
        feature_names = model_data['feature_names']
        algorithm = model_data['algorithm']
        
        # Подготавливаем features в правильном порядке
        # Если какого-то feature нет, используем 0
        X_input = np.array([[float(match_features.get(f, 0)) for f in feature_names]])
        
        # Предсказываем веса
        predictions = {}
        for weight_name, model in models.items():
            pred_value = model.predict(X_input)[0]
            
            # Ограничиваем диапазон весов 0.7 - 1.5
            pred_value = max(0.7, min(1.5, pred_value))
            
            predictions[weight_name] = float(pred_value)
        
        # Добавляем информацию об алгоритме
        predictions['algorithm'] = algorithm
        
        print(f"🤖 [{league}/{algorithm}] Предсказаны веса: h2h={predictions.get('h2h_weight', 1.0):.3f}, "
              f"motivation={predictions.get('motivation_weight', 1.0):.3f}, "
              f"streak={predictions.get('streak_weight', 1.0):.3f}")
        
        return predictions
        
    except Exception as e:
        print(f"❌ Ошибка предсказания весов: {e}")
        import traceback
        traceback.print_exc()
        return None


def clear_model_cache():
    """Очистить кэш моделей (используется после переобучения)"""
    global _model_cache
    _model_cache = {}
    print("🗑️ Кэш моделей очищен")
