"""
Модуль для работы с базой данных PostgreSQL
Хранение прогнозов, результатов матчей и обучение ML модели
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json


def get_connection():
    """Получить соединение с базой данных"""
    return psycopg2.connect(os.environ['DATABASE_URL'])


def init_database():
    """Инициализация таблиц базы данных"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Таблица для прогнозов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            match_id VARCHAR(100) UNIQUE,
            home_team VARCHAR(200),
            away_team VARCHAR(200),
            league VARCHAR(200),
            round_number VARCHAR(100),
            match_date TIMESTAMP,
            
            -- Прогнозы
            predicted_result VARCHAR(100),
            predicted_home_goals FLOAT,
            predicted_away_goals FLOAT,
            predicted_total FLOAT,
            confidence FLOAT,
            betting_tips TEXT,
            
            -- Факторы прогноза
            home_attack FLOAT,
            away_attack FLOAT,
            h2h_factor_home FLOAT,
            h2h_factor_away FLOAT,
            home_motivation FLOAT,
            away_motivation FLOAT,
            home_streak_factor FLOAT,
            away_streak_factor FLOAT,
            
            -- Новые факторы (10 ноября 2025)
            weather_adjustment FLOAT,
            injuries_home_count INTEGER,
            injuries_away_count INTEGER,
            halftime_adjustment FLOAT,
            playstyle_adjustment_home FLOAT,
            playstyle_adjustment_away FLOAT,
            
            -- Реальный результат (заполняется после матча)
            actual_result VARCHAR(100),
            actual_home_goals INTEGER,
            actual_away_goals INTEGER,
            actual_total INTEGER,
            
            -- Точность прогноза
            result_correct BOOLEAN,
            total_error FLOAT,
            
            -- Версия алгоритма
            algorithm_version VARCHAR(20) DEFAULT 'v2',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица для весов ML модели
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ml_weights (
            id SERIAL PRIMARY KEY,
            weight_name VARCHAR(100) UNIQUE,
            weight_value FLOAT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Инициализация начальных весов (включая новые факторы 10 ноября 2025)
    initial_weights = {
        'h2h_weight': 1.0,
        'motivation_weight': 1.0,
        'streak_weight': 1.0,
        'form_weight': 1.0,
        'position_weight': 1.0,
        'weather_weight': 1.0,
        'injuries_weight': 1.0,
        'halftime_weight': 1.0,
        'playstyle_weight': 1.0
    }
    
    for name, value in initial_weights.items():
        cur.execute("""
            INSERT INTO ml_weights (weight_name, weight_value)
            VALUES (%s, %s)
            ON CONFLICT (weight_name) DO NOTHING
        """, (name, value))
    
    # Таблица для статистики точности
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accuracy_stats (
            id SERIAL PRIMARY KEY,
            period VARCHAR(50),
            total_predictions INTEGER,
            correct_results INTEGER,
            accuracy_percentage FLOAT,
            avg_total_error FLOAT,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица для исторических матчей (для обучения ML)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historical_matches (
            id SERIAL PRIMARY KEY,
            match_id VARCHAR(100) UNIQUE,
            season VARCHAR(20),
            competition_id INTEGER,
            competition_name VARCHAR(200),
            
            -- Команды
            home_team_id INTEGER,
            home_team VARCHAR(200),
            away_team_id INTEGER,
            away_team VARCHAR(200),
            
            -- Время матча
            match_date TIMESTAMP,
            matchday INTEGER,
            
            -- Результат
            home_goals INTEGER,
            away_goals INTEGER,
            winner VARCHAR(20),
            
            -- Статистика домашней команды
            home_position INTEGER,
            home_points INTEGER,
            home_form VARCHAR(10),
            home_goals_for INTEGER,
            home_goals_against INTEGER,
            home_played INTEGER,
            home_won INTEGER,
            home_draw INTEGER,
            home_lost INTEGER,
            
            -- Статистика гостевой команды
            away_position INTEGER,
            away_points INTEGER,
            away_form VARCHAR(10),
            away_goals_for INTEGER,
            away_goals_against INTEGER,
            away_played INTEGER,
            away_won INTEGER,
            away_draw INTEGER,
            away_lost INTEGER,
            
            -- Дополнительные данные
            h2h_data JSONB,
            top_scorers JSONB,
            
            -- Метаданные
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Индексы для быстрого поиска
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_historical_season 
        ON historical_matches(season)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_historical_competition 
        ON historical_matches(competition_id)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_historical_date 
        ON historical_matches(match_date)
    """)
    
    # Таблица для подписок на команды
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            team_name VARCHAR(200) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, team_name)
        )
    """)
    
    # Индекс для быстрого поиска подписок
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscriptions_user 
        ON user_subscriptions(user_id)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscriptions_team 
        ON user_subscriptions(team_name)
    """)
    
    # Таблица для отслеживания отправленных уведомлений
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sent_notifications (
            id SERIAL PRIMARY KEY,
            match_id VARCHAR(100) NOT NULL,
            user_id BIGINT NOT NULL,
            notification_type VARCHAR(50) NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(match_id, user_id, notification_type)
        )
    """)
    
    # Индекс для быстрой проверки отправленных уведомлений
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_sent_notifications_match 
        ON sent_notifications(match_id, notification_type)
    """)
    
    # Таблица для метрик ML моделей (A/B тестирование + специализация по лигам)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ml_model_metrics (
            id SERIAL PRIMARY KEY,
            league VARCHAR(200) NOT NULL,
            algorithm VARCHAR(100) NOT NULL,
            
            -- Метрики точности для каждого веса
            h2h_r2_score FLOAT DEFAULT 0.0,
            motivation_r2_score FLOAT DEFAULT 0.0,
            streak_r2_score FLOAT DEFAULT 0.0,
            overall_accuracy FLOAT DEFAULT 0.0,
            
            -- Статистика обучения
            training_samples INTEGER DEFAULT 0,
            test_samples INTEGER DEFAULT 0,
            test_mse FLOAT DEFAULT 0.0,
            
            -- Метаданные
            last_trained TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT FALSE,
            model_version VARCHAR(50),
            
            UNIQUE(league, algorithm)
        )
    """)
    
    # Индексы для быстрого поиска лучших моделей
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_model_metrics_league 
        ON ml_model_metrics(league)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_model_metrics_active 
        ON ml_model_metrics(is_active)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_model_metrics_accuracy 
        ON ml_model_metrics(overall_accuracy DESC)
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ База данных инициализирована!")


def save_prediction(match_data, predictions, factors):
    """
    Сохранить прогноз в базу данных
    
    Args:
        match_data: Данные о матче
        predictions: Словарь с прогнозами
        factors: Словарь с факторами (h2h, motivation, streak)
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Извлекаем данные
    teams = match_data.get("teams", {})
    home_team = teams.get("home", {}).get("name", "Unknown")
    away_team = teams.get("away", {}).get("name", "Unknown")
    
    fixture = match_data.get("fixture", {})
    match_id = str(fixture.get("id", ""))
    match_date = fixture.get("date")
    
    league_data = match_data.get("league", {})
    league = league_data.get("name", "Unknown")
    round_number = league_data.get("round", "Unknown")
    
    # Определяем результат из predictions
    expected_result = predictions.get("expected_result", "")
    
    # Сохраняем betting_tips как JSON строку
    betting_tips = predictions.get("betting_tips", [])
    betting_tips_json = json.dumps(betting_tips, ensure_ascii=False) if betting_tips else ""
    
    # Извлекаем индивидуальные тоталы
    home_total_str = predictions.get("home_total", "0")
    away_total_str = predictions.get("away_total", "0")
    
    try:
        predicted_home_goals = float(home_total_str.split(":")[1].strip()) if ":" in home_total_str else 0
    except:
        predicted_home_goals = factors.get("home_attack", 0)
    
    try:
        predicted_away_goals = float(away_total_str.split(":")[1].strip()) if ":" in away_total_str else 0
    except:
        predicted_away_goals = factors.get("away_attack", 0)
    
    total_str = predictions.get("total_goals", "0")
    try:
        predicted_total = float(total_str.replace("Тотал:", "").replace("⚽", "").strip())
    except:
        predicted_total = 2.5
    
    confidence = predictions.get("confidence", 75.0)
    
    try:
        cur.execute("""
            INSERT INTO predictions (
                match_id, home_team, away_team, league, round_number, match_date,
                predicted_result, predicted_home_goals, predicted_away_goals, 
                predicted_total, confidence, betting_tips,
                home_attack, away_attack,
                h2h_factor_home, h2h_factor_away,
                home_motivation, away_motivation,
                home_streak_factor, away_streak_factor,
                weather_adjustment, injuries_home_count, injuries_away_count,
                halftime_adjustment, playstyle_adjustment_home, playstyle_adjustment_away,
                algorithm_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id) DO UPDATE SET
                predicted_result = EXCLUDED.predicted_result,
                predicted_total = EXCLUDED.predicted_total,
                confidence = EXCLUDED.confidence,
                betting_tips = EXCLUDED.betting_tips,
                weather_adjustment = EXCLUDED.weather_adjustment,
                injuries_home_count = EXCLUDED.injuries_home_count,
                injuries_away_count = EXCLUDED.injuries_away_count,
                halftime_adjustment = EXCLUDED.halftime_adjustment,
                playstyle_adjustment_home = EXCLUDED.playstyle_adjustment_home,
                playstyle_adjustment_away = EXCLUDED.playstyle_adjustment_away,
                algorithm_version = EXCLUDED.algorithm_version,
                updated_at = CURRENT_TIMESTAMP
        """, (
            match_id, home_team, away_team, league, round_number, match_date,
            expected_result, predicted_home_goals, predicted_away_goals,
            predicted_total, confidence, betting_tips_json,
            factors.get("home_attack", 0),
            factors.get("away_attack", 0),
            factors.get("h2h_factor_home", 1.0),
            factors.get("h2h_factor_away", 1.0),
            factors.get("home_motivation", 1.0),
            factors.get("away_motivation", 1.0),
            factors.get("home_streak_factor", 1.0),
            factors.get("away_streak_factor", 1.0),
            factors.get("weather_adjustment", 0.0),
            factors.get("injuries_home_count", 0),
            factors.get("injuries_away_count", 0),
            factors.get("halftime_adjustment", 0.0),
            factors.get("playstyle_adjustment_home", 0.0),
            factors.get("playstyle_adjustment_away", 0.0),
            'v2'  # Новый алгоритм после рефакторинга 7 ноября
        ))
        
        conn.commit()
    except Exception as e:
        print(f"❌ Ошибка сохранения прогноза: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def get_ml_weights():
    """Получить текущие веса ML модели"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT weight_name, weight_value FROM ml_weights")
    weights = {row['weight_name']: row['weight_value'] for row in cur.fetchall()}
    
    cur.close()
    conn.close()
    
    return weights


def update_ml_weights(weights):
    """Обновить веса ML модели"""
    conn = get_connection()
    cur = conn.cursor()
    
    for name, value in weights.items():
        cur.execute("""
            UPDATE ml_weights 
            SET weight_value = %s, updated_at = CURRENT_TIMESTAMP
            WHERE weight_name = %s
        """, (value, name))
    
    conn.commit()
    cur.close()
    conn.close()


def get_accuracy_stats(period='all', algorithm_version=None):
    """
    Получить статистику точности прогнозов
    
    Args:
        period: 'all', 'last_week', 'last_month'
        algorithm_version: None (все версии), 'v1' (старый), 'v2' (новый)
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN result_correct = TRUE THEN 1 END) as correct,
            COUNT(CASE WHEN result_correct = FALSE THEN 1 END) as incorrect,
            ROUND(AVG(CASE WHEN result_correct = TRUE THEN 100.0 ELSE 0 END)::NUMERIC, 1) as accuracy,
            ROUND(AVG(total_error)::NUMERIC, 2) as avg_error,
            -- Разбивка по типам прогнозов
            COUNT(CASE WHEN predicted_result LIKE 'Победа%' AND result_correct = TRUE THEN 1 END) as wins_correct,
            COUNT(CASE WHEN predicted_result LIKE 'Победа%' THEN 1 END) as wins_total,
            COUNT(CASE WHEN predicted_result = 'Ничья' AND result_correct = TRUE THEN 1 END) as draws_correct,
            COUNT(CASE WHEN predicted_result = 'Ничья' THEN 1 END) as draws_total
        FROM predictions
        WHERE actual_result IS NOT NULL
    """
    
    if period == 'last_week':
        query += " AND match_date > NOW() - INTERVAL '7 days'"
    elif period == 'last_month':
        query += " AND match_date > NOW() - INTERVAL '30 days'"
    
    if algorithm_version:
        query += f" AND algorithm_version = '{algorithm_version}'"
    
    cur.execute(query)
    stats = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return dict(stats) if stats else {}


def get_recent_predictions(limit=5):
    """Получить последние прогнозы с результатами"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            home_team,
            away_team,
            predicted_result,
            actual_result,
            result_correct,
            ROUND(total_error::numeric, 2) as total_error,
            algorithm_version,
            match_date
        FROM predictions
        WHERE actual_result IS NOT NULL
        ORDER BY match_date DESC
        LIMIT %s
    """, (limit,))
    
    results = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(row) for row in results]


def get_tournaments_with_predictions():
    """Получить список турниров, в которых есть прогнозы с результатами"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            league,
            COUNT(*) as total_predictions,
            COUNT(CASE WHEN result_correct = TRUE THEN 1 END) as correct_predictions,
            ROUND(AVG(CASE WHEN result_correct = TRUE THEN 100.0 ELSE 0 END)::NUMERIC, 1) as accuracy
        FROM predictions
        WHERE actual_result IS NOT NULL
        GROUP BY league
        ORDER BY total_predictions DESC
    """)
    
    tournaments = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(row) for row in tournaments]


def get_rounds_by_league(league_name):
    """Получить список туров для конкретного турнира"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            round_number,
            COUNT(*) as total_predictions,
            COUNT(CASE WHEN result_correct = TRUE THEN 1 END) as correct_predictions,
            ROUND(AVG(CASE WHEN result_correct = TRUE THEN 100.0 ELSE 0 END)::NUMERIC, 1) as accuracy,
            MAX(match_date) as latest_match
        FROM predictions
        WHERE actual_result IS NOT NULL AND league = %s
        GROUP BY round_number
        ORDER BY latest_match DESC
    """, (league_name,))
    
    rounds = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(row) for row in rounds]


def get_predictions_by_league(league_name):
    """Получить все прогнозы для конкретного турнира"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            home_team,
            away_team,
            predicted_result,
            predicted_home_goals,
            predicted_away_goals,
            predicted_total,
            actual_result,
            actual_home_goals,
            actual_away_goals,
            actual_total,
            result_correct,
            betting_tips,
            round_number,
            match_date
        FROM predictions
        WHERE league = %s AND actual_result IS NOT NULL
        ORDER BY match_date DESC
    """, (league_name,))
    
    predictions = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(row) for row in predictions]


def get_unverified_predictions(limit=100):
    """Получает все прогнозы с незаполненными результатами"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = """
            SELECT 
                id,
                match_id,
                league,
                home_team,
                away_team,
                match_date,
                predicted_result,
                predicted_home_goals,
                predicted_away_goals
            FROM predictions
            WHERE actual_home_goals IS NULL
            AND match_date < NOW()
            ORDER BY match_date DESC
            LIMIT %s
        """
        
        cur.execute(query, (limit,))
        predictions = cur.fetchall()
        
        return [dict(row) for row in predictions]
        
    except Exception as e:
        print(f"Ошибка получения непроверенных прогнозов: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def update_match_result(prediction_id, home_team, away_team, actual_home_goals, actual_away_goals, predicted_result):
    """Обновляет фактические результаты матча"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Определяем фактический результат
        if actual_home_goals > actual_away_goals:
            actual_result = f"Победа {home_team}"
            actual_result_type = "home_win"
        elif actual_away_goals > actual_home_goals:
            actual_result = f"Победа {away_team}"
            actual_result_type = "away_win"
        else:
            actual_result = "Ничья"
            actual_result_type = "draw"
        
        # Проверяем точность прогноза результата
        result_correct = False
        if actual_result_type == "home_win" and home_team in predicted_result and "Победа" in predicted_result:
            result_correct = True
        elif actual_result_type == "away_win" and away_team in predicted_result and "Победа" in predicted_result:
            result_correct = True
        elif actual_result_type == "draw" and "Ничья" in predicted_result:
            result_correct = True
        
        actual_total = actual_home_goals + actual_away_goals
        
        # Обновляем результаты
        cur.execute("""
            UPDATE predictions
            SET 
                actual_home_goals = %s,
                actual_away_goals = %s,
                actual_total = %s,
                actual_result = %s,
                result_correct = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (actual_home_goals, actual_away_goals, actual_total, actual_result, result_correct, prediction_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Ошибка обновления результата: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def track_user(user_id, username=None, first_name=None, last_name=None):
    """
    Отслеживание пользователя - создание или обновление записи
    
    Args:
        user_id: Telegram user ID
        username: Username пользователя
        first_name: Имя пользователя
        last_name: Фамилия пользователя
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Проверяем существует ли пользователь
        cur.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, total_actions)
            VALUES (%s, %s, %s, %s, 0)
            ON CONFLICT (user_id) DO UPDATE
            SET username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                last_seen = CURRENT_TIMESTAMP
        """, (user_id, username, first_name, last_name))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка отслеживания пользователя: {e}")
    finally:
        cur.close()
        conn.close()


def track_action(user_id, action_type, action_details=None):
    """
    Отслеживание действия пользователя
    
    Args:
        user_id: Telegram user ID
        action_type: Тип действия (analyze, stats, train, etc.)
        action_details: Дополнительные детали (JSON строка или текст)
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Сохраняем действие
        cur.execute("""
            INSERT INTO user_actions (user_id, action_type, action_details)
            VALUES (%s, %s, %s)
        """, (user_id, action_type, action_details))
        
        # Увеличиваем счетчик действий пользователя
        cur.execute("""
            UPDATE users
            SET total_actions = total_actions + 1,
                last_seen = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (user_id,))
        
        conn.commit()
        
        # Автоматически обновляем Excel файл
        try:
            from modules.analytics import update_excel_file
            update_excel_file()
        except Exception as excel_error:
            print(f"⚠️ Не удалось обновить Excel файл: {excel_error}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка отслеживания действия: {e}")
    finally:
        cur.close()
        conn.close()


def get_user_stats():
    """
    Получить общую статистику пользователей
    
    Returns:
        dict: Статистика (total_users, total_actions, active_users_today, etc.)
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Общее количество пользователей
        cur.execute("SELECT COUNT(*) as count FROM users")
        result = cur.fetchone()
        total_users = result['count'] if result else 0
        
        # Общее количество действий
        cur.execute("SELECT SUM(total_actions) as count FROM users")
        result = cur.fetchone()
        total_actions = result['count'] if result and result['count'] else 0
        
        # Активные пользователи за последние 24 часа
        cur.execute("""
            SELECT COUNT(*) as count FROM users
            WHERE last_seen >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
        """)
        result = cur.fetchone()
        active_today = result['count'] if result else 0
        
        # Активные пользователи за последние 7 дней
        cur.execute("""
            SELECT COUNT(*) as count FROM users
            WHERE last_seen >= CURRENT_TIMESTAMP - INTERVAL '7 days'
        """)
        result = cur.fetchone()
        active_week = result['count'] if result else 0
        
        # Топ-5 пользователей по активности
        cur.execute("""
            SELECT user_id, username, first_name, total_actions
            FROM users
            ORDER BY total_actions DESC
            LIMIT 5
        """)
        top_users = cur.fetchall()
        
        return {
            "total_users": total_users,
            "total_actions": total_actions,
            "active_today": active_today,
            "active_week": active_week,
            "top_users": top_users
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return {}
    finally:
        cur.close()
        conn.close()


def get_all_users_for_export():
    """
    Получить данные всех пользователей для экспорта в Excel
    
    Returns:
        list: Список пользователей с их статистикой
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                user_id,
                username,
                first_name,
                last_name,
                first_seen,
                last_seen,
                total_actions,
                is_active
            FROM users
            ORDER BY total_actions DESC
        """)
        users = cur.fetchall()
        return users
    except Exception as e:
        print(f"❌ Ошибка получения пользователей: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def save_historical_match(match_data):
    """
    Сохранить исторический матч в БД
    
    Args:
        match_data (dict): Данные матча с результатом и статистикой команд
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO historical_matches (
                match_id, season, competition_id, competition_name,
                home_team_id, home_team, away_team_id, away_team,
                match_date, matchday,
                home_goals, away_goals, winner,
                home_position, home_points, home_form,
                home_goals_for, home_goals_against, home_played,
                home_won, home_draw, home_lost,
                away_position, away_points, away_form,
                away_goals_for, away_goals_against, away_played,
                away_won, away_draw, away_lost,
                h2h_data, top_scorers
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (match_id) DO UPDATE SET
                home_goals = EXCLUDED.home_goals,
                away_goals = EXCLUDED.away_goals,
                winner = EXCLUDED.winner
        """, (
            match_data.get('match_id'),
            match_data.get('season'),
            match_data.get('competition_id'),
            match_data.get('competition_name'),
            match_data.get('home_team_id'),
            match_data.get('home_team'),
            match_data.get('away_team_id'),
            match_data.get('away_team'),
            match_data.get('match_date'),
            match_data.get('matchday'),
            match_data.get('home_goals'),
            match_data.get('away_goals'),
            match_data.get('winner'),
            match_data.get('home_position'),
            match_data.get('home_points'),
            match_data.get('home_form'),
            match_data.get('home_goals_for'),
            match_data.get('home_goals_against'),
            match_data.get('home_played'),
            match_data.get('home_won'),
            match_data.get('home_draw'),
            match_data.get('home_lost'),
            match_data.get('away_position'),
            match_data.get('away_points'),
            match_data.get('away_form'),
            match_data.get('away_goals_for'),
            match_data.get('away_goals_against'),
            match_data.get('away_played'),
            match_data.get('away_won'),
            match_data.get('away_draw'),
            match_data.get('away_lost'),
            json.dumps(match_data.get('h2h_data')),
            json.dumps(match_data.get('top_scorers'))
        ))
        
        conn.commit()
    except Exception as e:
        print(f"❌ Ошибка сохранения исторического матча: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def get_historical_matches(season=None, competition_id=None, limit=1000):
    """
    Получить исторические матчи из БД
    
    Args:
        season (str): Фильтр по сезону (например, "2023")
        competition_id (int): Фильтр по ID лиги
        limit (int): Максимальное количество записей
        
    Returns:
        list: Список исторических матчей
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = "SELECT * FROM historical_matches WHERE 1=1"
        params = []
        
        if season:
            query += " AND season = %s"
            params.append(season)
        
        if competition_id:
            query += " AND competition_id = %s"
            params.append(competition_id)
        
        query += " ORDER BY match_date DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        matches = cur.fetchall()
        return matches
    except Exception as e:
        print(f"❌ Ошибка получения исторических матчей: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_historical_stats():
    """
    Получить статистику по исторической базе
    
    Returns:
        dict: Статистика (total_matches, seasons, competitions, etc.)
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Общее количество матчей
        cur.execute("SELECT COUNT(*) as count FROM historical_matches")
        result = cur.fetchone()
        total_matches = result['count'] if result else 0
        
        # Количество уникальных сезонов
        cur.execute("SELECT COUNT(DISTINCT season) as count FROM historical_matches")
        result = cur.fetchone()
        seasons_count = result['count'] if result else 0
        
        # Количество уникальных лиг
        cur.execute("SELECT COUNT(DISTINCT competition_id) as count FROM historical_matches")
        result = cur.fetchone()
        competitions_count = result['count'] if result else 0
        
        # Список сезонов
        cur.execute("SELECT DISTINCT season FROM historical_matches ORDER BY season DESC")
        seasons = [row['season'] for row in cur.fetchall()]
        
        # Список лиг
        cur.execute("""
            SELECT DISTINCT competition_id, competition_name 
            FROM historical_matches 
            ORDER BY competition_name
        """)
        competitions = cur.fetchall()
        
        return {
            "total_matches": total_matches,
            "seasons_count": seasons_count,
            "competitions_count": competitions_count,
            "seasons": seasons,
            "competitions": competitions
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return {}
    finally:
        cur.close()
        conn.close()


def add_subscription(user_id, team_name):
    """
    Добавить подписку пользователя на команду
    
    Args:
        user_id (int): ID пользователя Telegram
        team_name (str): Название команды
        
    Returns:
        bool: True если подписка добавлена, False если уже существует
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO user_subscriptions (user_id, team_name)
            VALUES (%s, %s)
            ON CONFLICT (user_id, team_name) DO NOTHING
        """, (user_id, team_name))
        
        added = cur.rowcount > 0
        conn.commit()
        return added
    except Exception as e:
        print(f"❌ Ошибка добавления подписки: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def remove_subscription(user_id, team_name):
    """
    Удалить подписку пользователя на команду
    
    Args:
        user_id (int): ID пользователя Telegram
        team_name (str): Название команды
        
    Returns:
        bool: True если подписка удалена, False если не существовала
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM user_subscriptions 
            WHERE user_id = %s AND team_name = %s
        """, (user_id, team_name))
        
        removed = cur.rowcount > 0
        conn.commit()
        return removed
    except Exception as e:
        print(f"❌ Ошибка удаления подписки: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def get_user_subscriptions(user_id):
    """
    Получить все подписки пользователя
    
    Args:
        user_id (int): ID пользователя Telegram
        
    Returns:
        list: Список названий команд
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT team_name, created_at 
            FROM user_subscriptions 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        return cur.fetchall()
    except Exception as e:
        print(f"❌ Ошибка получения подписок: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_team_subscribers(team_name):
    """
    Получить всех подписчиков команды
    
    Args:
        team_name (str): Название команды
        
    Returns:
        list: Список user_id подписчиков
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT user_id 
            FROM user_subscriptions 
            WHERE team_name = %s
        """, (team_name,))
        
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"❌ Ошибка получения подписчиков: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_all_subscribed_teams():
    """
    Получить список всех команд, на которые есть подписки
    
    Returns:
        list: Список уникальных названий команд
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT DISTINCT team_name 
            FROM user_subscriptions
            ORDER BY team_name
        """)
        
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"❌ Ошибка получения списка команд: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def is_notification_sent(match_id, user_id, notification_type='2h_before'):
    """
    Проверить, было ли уже отправлено уведомление
    
    Args:
        match_id (str): ID матча
        user_id (int): ID пользователя
        notification_type (str): Тип уведомления (по умолчанию '2h_before')
        
    Returns:
        bool: True если уведомление уже отправлено
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT COUNT(*) FROM sent_notifications
            WHERE match_id = %s AND user_id = %s AND notification_type = %s
        """, (match_id, user_id, notification_type))
        
        result = cur.fetchone()
        count = result[0] if result else 0
        return count > 0
    except Exception as e:
        print(f"❌ Ошибка проверки уведомления: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def mark_notification_sent(match_id, user_id, notification_type='2h_before'):
    """
    Отметить уведомление как отправленное
    
    Args:
        match_id (str): ID матча
        user_id (int): ID пользователя
        notification_type (str): Тип уведомления (по умолчанию '2h_before')
        
    Returns:
        bool: True если запись добавлена успешно
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO sent_notifications (match_id, user_id, notification_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (match_id, user_id, notification_type) DO NOTHING
        """, (match_id, user_id, notification_type))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка записи уведомления: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def get_notified_users_for_match(match_id, notification_type='2h_before'):
    """
    Получить список user_id, которым уже отправлены уведомления для матча
    Bulk-операция для оптимизации производительности
    
    Args:
        match_id (str): ID матча
        notification_type (str): Тип уведомления
        
    Returns:
        set: Множество user_id, которые уже получили уведомление
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT user_id FROM sent_notifications
            WHERE match_id = %s AND notification_type = %s
        """, (match_id, notification_type))
        
        return set(row[0] for row in cur.fetchall())
    except Exception as e:
        print(f"❌ Ошибка получения уведомленных пользователей: {e}")
        return set()
    finally:
        cur.close()
        conn.close()


def mark_notifications_sent_bulk(match_id, user_ids, notification_type='2h_before'):
    """
    Массовая отметка уведомлений как отправленных
    Оптимизировано для больших списков подписчиков
    
    Args:
        match_id (str): ID матча
        user_ids (list): Список user_id
        notification_type (str): Тип уведомления
        
    Returns:
        int: Количество добавленных записей
    """
    if not user_ids:
        return 0
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Используем executemany для batch insert
        values = [(match_id, user_id, notification_type) for user_id in user_ids]
        cur.executemany("""
            INSERT INTO sent_notifications (match_id, user_id, notification_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (match_id, user_id, notification_type) DO NOTHING
        """, values)
        
        inserted = cur.rowcount
        conn.commit()
        return inserted
    except Exception as e:
        print(f"❌ Ошибка bulk записи уведомлений: {e}")
        conn.rollback()
        return 0
    finally:
        cur.close()
        conn.close()


def save_model_metrics(league, algorithm, metrics):
    """
    Сохранить метрики ML модели
    
    Args:
        league (str): Название лиги ('Premier League', 'La Liga', etc.)
        algorithm (str): Алгоритм ('GradientBoosting', 'RandomForest', 'XGBoost')
        metrics (dict): Словарь с метриками:
            - h2h_r2_score
            - motivation_r2_score
            - streak_r2_score
            - overall_accuracy
            - training_samples
            - test_samples
            - test_mse
            - is_active
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO ml_model_metrics (
                league, algorithm, h2h_r2_score, motivation_r2_score, 
                streak_r2_score, overall_accuracy, training_samples, 
                test_samples, test_mse, is_active, model_version, last_trained
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (league, algorithm) 
            DO UPDATE SET
                h2h_r2_score = EXCLUDED.h2h_r2_score,
                motivation_r2_score = EXCLUDED.motivation_r2_score,
                streak_r2_score = EXCLUDED.streak_r2_score,
                overall_accuracy = EXCLUDED.overall_accuracy,
                training_samples = EXCLUDED.training_samples,
                test_samples = EXCLUDED.test_samples,
                test_mse = EXCLUDED.test_mse,
                is_active = EXCLUDED.is_active,
                model_version = EXCLUDED.model_version,
                last_trained = CURRENT_TIMESTAMP
        """, (
            league,
            algorithm,
            metrics.get('h2h_r2_score', 0.0),
            metrics.get('motivation_r2_score', 0.0),
            metrics.get('streak_r2_score', 0.0),
            metrics.get('overall_accuracy', 0.0),
            metrics.get('training_samples', 0),
            metrics.get('test_samples', 0),
            metrics.get('test_mse', 0.0),
            metrics.get('is_active', False),
            metrics.get('model_version', 'v1')
        ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения метрик модели: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def get_best_model_for_league(league):
    """
    Получить лучшую активную модель для лиги
    
    Args:
        league (str): Название лиги
        
    Returns:
        dict: Метрики лучшей модели или None
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT * FROM ml_model_metrics
            WHERE league = %s AND is_active = TRUE
            ORDER BY overall_accuracy DESC
            LIMIT 1
        """, (league,))
        
        return cur.fetchone()
    except Exception as e:
        print(f"❌ Ошибка получения лучшей модели: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def get_all_model_metrics():
    """
    Получить метрики всех моделей
    
    Returns:
        list: Список словарей с метриками моделей
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT * FROM ml_model_metrics
            ORDER BY league, overall_accuracy DESC
        """)
        
        return cur.fetchall()
    except Exception as e:
        print(f"❌ Ошибка получения метрик моделей: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def set_active_model(league, algorithm):
    """
    Установить модель как активную (деактивировать остальные для этой лиги)
    
    Args:
        league (str): Название лиги
        algorithm (str): Алгоритм модели
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Деактивировать все модели для этой лиги
        cur.execute("""
            UPDATE ml_model_metrics
            SET is_active = FALSE
            WHERE league = %s
        """, (league,))
        
        # Активировать выбранную модель
        cur.execute("""
            UPDATE ml_model_metrics
            SET is_active = TRUE
            WHERE league = %s AND algorithm = %s
        """, (league, algorithm))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка установки активной модели: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


# Инициализация при импорте
try:
    init_database()
except Exception as e:
    print(f"⚠️ Ошибка инициализации БД: {e}")
