"""
Локальная ML модель для предсказания оптимальных весов факторов
Обучается на исторических данных вместо использования OpenAI API
"""
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
from datetime import datetime
from modules.database import get_historical_matches, get_connection
from psycopg2.extras import RealDictCursor


MODEL_PATH = "ml_models/"
WEIGHTS_TO_PREDICT = ['h2h_weight', 'motivation_weight', 'streak_weight']


def ensure_model_dir():
    """Создать директорию для моделей если её нет"""
    if not os.path.exists(MODEL_PATH):
        os.makedirs(MODEL_PATH)
        print(f"✅ Создана директория {MODEL_PATH}")


def prepare_training_data():
    """
    Подготовить данные для обучения из исторических матчей
    
    Returns:
        tuple: (X_features, y_targets, feature_names)
    """
    print("\n📊 Подготовка данных для обучения...")
    
    # Получаем исторические матчи
    matches = get_historical_matches(limit=5000)
    
    if not matches or len(matches) < 50:
        print(f"❌ Недостаточно данных: {len(matches) if matches else 0} матчей")
        return None, None, None
    
    print(f"✅ Загружено {len(matches)} исторических матчей")
    
    # Преобразуем в DataFrame
    df = pd.DataFrame(matches)
    
    # Создаём признаки (features) для каждого матча
    features = []
    targets = []
    
    for _, match in df.iterrows():
        # Пропускаем матчи без результата
        if match['home_goals'] is None or match['away_goals'] is None:
            continue
        
        # Пропускаем матчи без статистики команд
        if not match['home_position'] or not match['away_position']:
            continue
        
        # Фичи (то, что модель использует для предсказания)
        match_features = {
            # Разница в позициях в таблице
            'position_diff': abs(match['home_position'] - match['away_position']),
            'home_position': match['home_position'],
            'away_position': match['away_position'],
            
            # Статистика команд
            'home_goals_for': match['home_goals_for'] or 0,
            'home_goals_against': match['home_goals_against'] or 0,
            'away_goals_for': match['away_goals_for'] or 0,
            'away_goals_against': match['away_goals_against'] or 0,
            
            # Форма команд (количество побед в последних 5 матчах)
            'home_form_wins': match['home_form'].count('W') if match['home_form'] else 0,
            'away_form_wins': match['away_form'].count('W') if match['away_form'] else 0,
            
            # Разница голов
            'home_goal_diff': (match['home_goals_for'] or 0) - (match['home_goals_against'] or 0),
            'away_goal_diff': (match['away_goals_for'] or 0) - (match['away_goals_against'] or 0),
            
            # Очки команд
            'home_points': match['home_points'] or 0,
            'away_points': match['away_points'] or 0,
            'points_diff': abs((match['home_points'] or 0) - (match['away_points'] or 0)),
        }
        
        # Целевая переменная (то, что модель должна предсказать)
        # Рассчитываем "идеальные" веса на основе реального результата
        actual_home_goals = match['home_goals']
        actual_away_goals = match['away_goals']
        total_goals = actual_home_goals + actual_away_goals
        
        # Логика: если результат неожиданный (слабый обыграл сильного) -> H2H важнее
        # Если всё по ожиданиям -> мотивация и форма важнее
        position_favorite = 'home' if match['home_position'] < match['away_position'] else 'away'
        result_winner = 'home' if actual_home_goals > actual_away_goals else ('away' if actual_away_goals > actual_home_goals else 'draw')
        
        # Базовые веса
        h2h_weight = 1.0
        motivation_weight = 1.0
        streak_weight = 1.0
        
        # Корректировка весов на основе результата
        if result_winner != position_favorite and result_winner != 'draw':
            # Неожиданный результат -> H2H и streak важнее
            h2h_weight = 1.3
            streak_weight = 1.2
            motivation_weight = 0.9
        elif total_goals > 3:
            # Результативный матч -> мотивация важна
            motivation_weight = 1.3
            h2h_weight = 0.9
        elif total_goals < 2:
            # Низкая результативность -> форма и оборона важнее
            streak_weight = 1.2
            motivation_weight = 1.1
        
        features.append(match_features)
        targets.append({
            'h2h_weight': h2h_weight,
            'motivation_weight': motivation_weight,
            'streak_weight': streak_weight
        })
    
    if not features:
        print("❌ Не удалось подготовить данные для обучения")
        return None, None, None
    
    # Преобразуем в numpy arrays
    X_df = pd.DataFrame(features)
    y_df = pd.DataFrame(targets)
    
    print(f"\n✅ Подготовлено {len(X_df)} примеров для обучения")
    print(f"📋 Признаки: {list(X_df.columns)}")
    print(f"🎯 Целевые переменные: {list(y_df.columns)}")
    
    return X_df.values, y_df.values, list(X_df.columns)


def train_model():
    """
    Обучить ML модель на исторических данных
    
    Returns:
        dict: Результаты обучения (точность, ошибки, путь к модели)
    """
    ensure_model_dir()
    
    print("\n🧠 Начинаем обучение локальной ML модели...")
    
    # Подготовка данных
    X, y, feature_names = prepare_training_data()
    
    if X is None or len(X) < 50:
        return {
            "success": False,
            "error": "Недостаточно данных для обучения"
        }
    
    # Разделение на train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print(f"\n📊 Размер обучающей выборки: {len(X_train)}")
    print(f"📊 Размер тестовой выборки: {len(X_test)}")
    
    # Обучаем отдельную модель для каждого веса
    models = {}
    metrics = {}
    
    for i, weight_name in enumerate(WEIGHTS_TO_PREDICT):
        print(f"\n🎯 Обучение модели для '{weight_name}'...")
        
        # Создаём модель
        model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            random_state=42,
            verbose=0
        )
        
        # Обучаем
        model.fit(X_train, y_train[:, i])
        
        # Предсказания на тесте
        y_pred = model.predict(X_test)
        
        # Метрики
        mse = mean_squared_error(y_test[:, i], y_pred)
        r2 = r2_score(y_test[:, i], y_pred)
        
        print(f"   MSE: {mse:.4f}")
        print(f"   R²: {r2:.4f}")
        
        # Важность признаков
        feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"   Топ-3 важных признака:")
        for _, row in feature_importance.head(3).iterrows():
            print(f"      - {row['feature']}: {row['importance']:.3f}")
        
        models[weight_name] = model
        metrics[weight_name] = {
            'mse': float(mse),
            'r2': float(r2),
            'feature_importance': feature_importance.to_dict('records')
        }
    
    # Сохраняем модели
    model_file = f"{MODEL_PATH}football_weights_model.joblib"
    joblib.dump({
        'models': models,
        'feature_names': feature_names,
        'trained_at': datetime.now().isoformat(),
        'training_size': len(X),  # ИСПРАВЛЕНО: сохраняем ПОЛНЫЙ объём данных
        'test_size': len(X_test),
        'metrics': metrics
    }, model_file)
    
    print(f"\n✅ Модель сохранена: {model_file}")
    
    return {
        "success": True,
        "model_path": model_file,
        "training_size": len(X_train),
        "test_size": len(X_test),
        "metrics": metrics
    }


def predict_weights(match_features):
    """
    Предсказать оптимальные веса для матча
    
    Args:
        match_features (dict): Признаки матча (позиции, форма, голы и т.д.)
        
    Returns:
        dict: Предсказанные веса или None если модель не загружена
    """
    model_file = f"{MODEL_PATH}football_weights_model.joblib"
    
    # Проверяем наличие модели
    if not os.path.exists(model_file):
        print("⚠️ Локальная ML модель не найдена")
        return None
    
    try:
        # Загружаем модель
        saved_data = joblib.load(model_file)
        models = saved_data['models']
        feature_names = saved_data['feature_names']
        
        # Подготавливаем features в правильном порядке
        X_input = np.array([[match_features.get(f, 0) for f in feature_names]])
        
        # Предсказания
        predictions = {}
        for weight_name, model in models.items():
            pred_value = model.predict(X_input)[0]
            # Ограничиваем диапазон весов 0.7 - 1.5
            predictions[weight_name] = float(np.clip(pred_value, 0.7, 1.5))
        
        print(f"🤖 Локальная ML модель: {predictions}")
        return predictions
        
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        return None


def get_model_info():
    """Получить информацию о текущей модели"""
    model_file = f"{MODEL_PATH}football_weights_model.joblib"
    
    if not os.path.exists(model_file):
        return {
            "exists": False,
            "message": "Модель не обучена"
        }
    
    try:
        saved_data = joblib.load(model_file)
        return {
            "exists": True,
            "trained_at": saved_data.get('trained_at'),
            "training_size": saved_data.get('training_size'),
            "metrics": saved_data.get('metrics'),
            "feature_names": saved_data.get('feature_names')
        }
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Тестовое обучение
    result = train_model()
    
    if result['success']:
        print("\n" + "="*60)
        print("🎉 ОБУЧЕНИЕ ЗАВЕРШЕНО!")
        print("="*60)
        print(f"Обучено примеров: {result['training_size']}")
        print(f"Протестировано примеров: {result['test_size']}")
        print(f"\nМетрики:")
        for weight, metrics in result['metrics'].items():
            print(f"  {weight}: R² = {metrics['r2']:.3f}, MSE = {metrics['mse']:.4f}")
    else:
        print(f"\n❌ Ошибка: {result.get('error')}")
