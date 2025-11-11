"""
Модуль для A/B тестирования и специализации моделей по лигам
Обучает 3 алгоритма (GradientBoosting, RandomForest, XGBoost) для каждой из 5 лиг
"""
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb
from modules.database import get_historical_matches, save_model_metrics, set_active_model

# Директория для моделей
MODEL_PATH = "ml_models/"

# Топ-5 лиг для специализации
TOP_LEAGUES = [
    'Premier League',
    'La Liga',
    'Bundesliga',
    'Serie A',
    'Ligue 1'
]

# Алгоритмы для A/B тестирования
ALGORITHMS = {
    'GradientBoosting': {
        'class': GradientBoostingRegressor,
        'params': {
            'n_estimators': 100,
            'learning_rate': 0.1,
            'max_depth': 3,
            'random_state': 42
        }
    },
    'RandomForest': {
        'class': RandomForestRegressor,
        'params': {
            'n_estimators': 100,
            'max_depth': 10,
            'random_state': 42
        }
    },
    'XGBoost': {
        'class': xgb.XGBRegressor,
        'params': {
            'n_estimators': 100,
            'learning_rate': 0.1,
            'max_depth': 3,
            'random_state': 42,
            'objective': 'reg:squarederror'
        }
    }
}

# Веса для предсказания
WEIGHTS_TO_PREDICT = ['h2h_weight', 'motivation_weight', 'streak_weight']


def ensure_model_dir():
    """Создать директорию для моделей если её нет"""
    if not os.path.exists(MODEL_PATH):
        os.makedirs(MODEL_PATH)
        print(f"✅ Создана директория {MODEL_PATH}")


def prepare_training_data_for_league(league):
    """
    Подготовить данные для обучения для конкретной лиги
    
    Args:
        league (str): Название лиги
        
    Returns:
        tuple: (X_features, y_targets, feature_names) или (None, None, None)
    """
    print(f"\n📊 Подготовка данных для {league}...")
    
    # Получаем исторические матчи только для этой лиги
    matches = get_historical_matches(limit=5000)
    
    if not matches:
        print(f"❌ Нет данных для {league}")
        return None, None, None
    
    # Фильтруем только матчи этой лиги
    df = pd.DataFrame(matches)
    df = df[df['competition_name'] == league]
    
    if len(df) < 50:
        print(f"❌ Недостаточно данных для {league}: {len(df)} матчей")
        return None, None, None
    
    print(f"✅ Загружено {len(df)} матчей для {league}")
    
    # Создаём признаки (features) для каждого матча
    features = []
    targets = []
    
    for _, match in df.iterrows():
        # Пропускаем матчи без результата
        if pd.isna(match['home_goals']) or pd.isna(match['away_goals']):
            continue
        
        # Пропускаем матчи без статистики команд
        if pd.isna(match['home_position']) or pd.isna(match['away_position']):
            continue
        
        # Безопасное получение числовых значений с защитой от NaN
        def safe_num(val, default=0):
            """Безопасное преобразование в число с защитой от NaN"""
            return default if pd.isna(val) else (val if val is not None else default)
        
        def safe_str(val):
            """Безопасное получение строки с защитой от NaN"""
            return "" if pd.isna(val) or val is None else str(val)
        
        # Фичи (то, что модель использует для предсказания)
        home_goals_for = safe_num(match['home_goals_for'])
        home_goals_against = safe_num(match['home_goals_against'])
        away_goals_for = safe_num(match['away_goals_for'])
        away_goals_against = safe_num(match['away_goals_against'])
        home_points = safe_num(match['home_points'])
        away_points = safe_num(match['away_points'])
        home_won = safe_num(match['home_won'])
        away_won = safe_num(match['away_won'])
        home_played = safe_num(match['home_played'], 1)
        away_played = safe_num(match['away_played'], 1)
        
        match_features = {
            # Разница в позициях в таблице
            'position_diff': abs(match['home_position'] - match['away_position']),
            'home_position': float(match['home_position']),
            'away_position': float(match['away_position']),
            
            # Статистика команд
            'home_goals_for': float(home_goals_for),
            'home_goals_against': float(home_goals_against),
            'away_goals_for': float(away_goals_for),
            'away_goals_against': float(away_goals_against),
            
            # Форма команд (количество побед в последних 5 матчах)
            'home_form_wins': float(safe_str(match['home_form']).count('W')),
            'away_form_wins': float(safe_str(match['away_form']).count('W')),
            
            # Разница голов
            'home_goal_diff': float(home_goals_for - home_goals_against),
            'away_goal_diff': float(away_goals_for - away_goals_against),
            
            # Очки команд
            'home_points': float(home_points),
            'away_points': float(away_points),
            'points_diff': abs(float(home_points - away_points)),
            
            # Соотношение побед/поражений
            'home_win_ratio': float(home_won) / max(float(home_played), 1.0),
            'away_win_ratio': float(away_won) / max(float(away_played), 1.0)
        }
        
        # Целевые значения (веса, которые модель должна предсказать)
        # Базовые веса = 1.0, корректируем в зависимости от результата
        h2h_weight = 1.0
        motivation_weight = 1.0
        streak_weight = 1.0
        
        # Определяем результат матча
        home_goals = match['home_goals']
        away_goals = match['away_goals']
        
        # Анализируем результат для настройки весов
        if home_goals > away_goals:
            # Победа хозяев
            if match['home_position'] > match['away_position']:
                # Аутсайдер победил фаворита -> увеличиваем мотивацию и серию
                motivation_weight = 1.3
                streak_weight = 1.2
        elif away_goals > home_goals:
            # Победа гостей
            if match['away_position'] > match['home_position']:
                # Аутсайдер победил фаворита -> увеличиваем мотивацию
                motivation_weight = 1.3
                streak_weight = 1.2
        
        match_targets = {
            'h2h_weight': h2h_weight,
            'motivation_weight': motivation_weight,
            'streak_weight': streak_weight
        }
        
        features.append(match_features)
        targets.append(match_targets)
    
    if not features:
        print(f"❌ Не удалось извлечь признаки для {league}")
        return None, None, None
    
    # Преобразуем в numpy массивы
    feature_names = list(features[0].keys())
    X = np.array([[f[name] for name in feature_names] for f in features])
    
    # Создаём y для каждого веса
    y = {
        weight: np.array([t[weight] for t in targets])
        for weight in WEIGHTS_TO_PREDICT
    }
    
    print(f"✅ Подготовлено {len(X)} примеров с {len(feature_names)} признаками")
    
    return X, y, feature_names


def train_model_for_league_and_algorithm(league, algorithm_name):
    """
    Обучить модель для конкретной лиги и алгоритма
    
    Args:
        league (str): Название лиги
        algorithm_name (str): Название алгоритма
        
    Returns:
        dict: Метрики модели
    """
    print(f"\n🤖 Обучение {algorithm_name} для {league}...")
    
    # Подготовка данных
    X, y, feature_names = prepare_training_data_for_league(league)
    
    if X is None:
        return None
    
    # Разделяем на train/test
    X_train, X_test = train_test_split(X, test_size=0.2, random_state=42)
    
    # Получаем конфигурацию алгоритма
    algo_config = ALGORITHMS[algorithm_name]
    
    # Обучаем модель для каждого веса
    models = {}
    metrics = {
        'h2h_r2_score': 0.0,
        'motivation_r2_score': 0.0,
        'streak_r2_score': 0.0,
        'overall_accuracy': 0.0,
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'test_mse': 0.0,
        'model_version': 'v3',
        'is_active': False
    }
    
    r2_scores = []
    mse_scores = []
    
    for weight_name in WEIGHTS_TO_PREDICT:
        y_train, y_test = train_test_split(y[weight_name], test_size=0.2, random_state=42)
        
        # Создаём и обучаем модель
        model = algo_config['class'](**algo_config['params'])
        model.fit(X_train, y_train)
        
        # Предсказания
        y_pred = model.predict(X_test)
        
        # Метрики
        r2 = r2_score(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        
        r2_scores.append(r2)
        mse_scores.append(mse)
        
        # Сохраняем модель
        models[weight_name] = model
        
        # Записываем метрики
        metrics[f'{weight_name.replace("_weight", "")}_r2_score'] = float(r2)
        
        print(f"  {weight_name}: R² = {r2:.3f}, MSE = {mse:.3f}")
    
    # Общие метрики
    metrics['overall_accuracy'] = float(np.mean(r2_scores))
    metrics['test_mse'] = float(np.mean(mse_scores))
    
    # Сохраняем модели на диск
    ensure_model_dir()
    model_filename = f"{MODEL_PATH}{league.replace(' ', '_')}_{algorithm_name}.pkl"
    joblib.dump({
        'models': models,
        'feature_names': feature_names,
        'metrics': metrics
    }, model_filename)
    
    print(f"✅ Модель сохранена: {model_filename}")
    print(f"📊 Общая точность (R²): {metrics['overall_accuracy']:.3f}")
    
    # Сохраняем метрики в БД
    save_model_metrics(league, algorithm_name, metrics)
    
    return metrics


def train_all_models():
    """
    Обучить все комбинации лиг и алгоритмов (5 лиг × 3 алгоритма = 15 моделей)
    """
    print("🚀 Начало обучения всех моделей...")
    print(f"Лиги: {len(TOP_LEAGUES)}")
    print(f"Алгоритмы: {len(ALGORITHMS)}")
    print(f"Всего моделей: {len(TOP_LEAGUES) * len(ALGORITHMS)}\n")
    
    results = []
    
    for league in TOP_LEAGUES:
        print(f"\n{'='*60}")
        print(f"🏆 Лига: {league}")
        print(f"{'='*60}")
        
        league_results = {}
        
        for algorithm_name in ALGORITHMS.keys():
            metrics = train_model_for_league_and_algorithm(league, algorithm_name)
            
            if metrics:
                league_results[algorithm_name] = metrics
        
        # Выбираем лучшую модель для этой лиги
        if league_results:
            best_algo = max(league_results.items(), key=lambda x: x[1]['overall_accuracy'])
            print(f"\n🏆 Лучшая модель для {league}: {best_algo[0]} (R² = {best_algo[1]['overall_accuracy']:.3f})")
            
            # Активируем лучшую модель
            set_active_model(league, best_algo[0])
            
            results.append({
                'league': league,
                'best_algorithm': best_algo[0],
                'accuracy': best_algo[1]['overall_accuracy']
            })
    
    print("\n" + "="*60)
    print("✅ Обучение завершено!")
    print("="*60)
    
    print("\n📊 Сводка по лигам:")
    for result in results:
        print(f"  {result['league']}: {result['best_algorithm']} (R² = {result['accuracy']:.3f})")
    
    # Очищаем кэш моделей чтобы predictor.py загрузил новые версии
    try:
        from modules.ml_model_service import clear_model_cache
        clear_model_cache()
    except:
        pass
    
    return results


def load_model_for_league(league):
    """
    Загрузить лучшую активную модель для лиги
    
    Args:
        league (str): Название лиги
        
    Returns:
        dict: Модели и метаданные или None
    """
    from modules.database import get_best_model_for_league
    
    # Получаем информацию о лучшей модели из БД
    best_model_info = get_best_model_for_league(league)
    
    if not best_model_info:
        print(f"⚠️ Нет активной модели для {league}")
        return None
    
    algorithm = best_model_info['algorithm']
    model_filename = f"{MODEL_PATH}{league.replace(' ', '_')}_{algorithm}.pkl"
    
    try:
        loaded_data = joblib.load(model_filename)
        print(f"✅ Загружена модель {algorithm} для {league} (R² = {best_model_info['overall_accuracy']:.3f})")
        return loaded_data
    except Exception as e:
        print(f"❌ Ошибка загрузки модели {model_filename}: {e}")
        return None


if __name__ == "__main__":
    # Запуск обучения всех моделей
    train_all_models()
