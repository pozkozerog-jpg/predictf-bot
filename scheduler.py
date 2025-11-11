"""
Запускается по cron (Actions), делает один проход:
 - получает ближайшие матчи
 - для матчей за 110..130 минут отправляет уведомления подписчикам команд
 - для матчей за 50..70 минут до кик-офф проверяет наличие составов
 - если составы есть -> делает анализ и рассылает в канал и всем подписанным пользователям
"""
import os
from modules.data_fetcher import get_upcoming_matches, get_lineups, get_team_stats
from modules.odds_fetcher import fetch_odds as fetch_odds_global
from modules.predictor import generate
from modules.message_formatter import format_match_analysis
from modules.database import get_team_subscribers, get_notified_users_for_match, mark_notifications_sent_bulk
import json
from datetime import datetime, timezone, timedelta
import pytz
import telebot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
if not TOKEN:
    raise SystemExit("TELEGRAM_TOKEN not set")
bot = telebot.TeleBot(TOKEN)
USERS_FILE = "users.json"
UTC = pytz.UTC

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def notify_subscribers():
    """
    Уведомляет подписчиков за 2 часа до матча их команд
    Проверяет матчи за 110-130 минут до начала
    Каждый подписчик получает уведомление только один раз на матч
    """
    now = datetime.utcnow().replace(tzinfo=UTC)
    matches = get_upcoming_matches(next_n=200, window_hours=72)
    
    total_matches_checked = 0
    total_subscribers_notified = 0
    
    for m in matches:
        minutes = (m["kick_off"] - now).total_seconds() / 60
        
        # Проверяем окно 110-130 минут (примерно 2 часа до матча)
        if 110 <= minutes <= 130:
            total_matches_checked += 1
            match_id = str(m.get("id", ""))
            home_team = m.get("home", "")
            away_team = m.get("away", "")
            league = m.get("competition", "")
            kick_off_local = m["kick_off"].strftime("%H:%M")
            
            # Получаем подписчиков обеих команд
            home_subscribers = get_team_subscribers(home_team)
            away_subscribers = get_team_subscribers(away_team)
            
            # Объединяем уникальные подписки
            all_subscribers = set(home_subscribers + away_subscribers)
            
            if all_subscribers:
                # Получаем список уже уведомленных пользователей (BULK запрос)
                already_notified = get_notified_users_for_match(match_id, '2h_before')
                
                # Фильтруем в памяти
                pending_subscribers = all_subscribers - already_notified
                
                if pending_subscribers:
                    # Форматируем сообщение
                    notification_text = (
                        f"🔔 <b>Матч начнется через 2 часа!</b>\n\n"
                        f"🏆 {league}\n"
                        f"⚽ {home_team} vs {away_team}\n"
                        f"🕐 Начало: {kick_off_local} UTC\n\n"
                        f"<i>Подробный прогноз будет за час до матча</i>"
                    )
                    
                    successfully_notified = []
                    # Отправляем уведомления только новым подписчикам
                    for user_id in pending_subscribers:
                        try:
                            bot.send_message(user_id, notification_text, parse_mode="HTML")
                            successfully_notified.append(user_id)
                        except Exception as e:
                            print(f"⚠️ Не удалось отправить уведомление пользователю {user_id}: {e}")
                            continue
                    
                    # Массово отмечаем отправленные уведомления (BULK insert)
                    if successfully_notified:
                        inserted = mark_notifications_sent_bulk(match_id, successfully_notified, '2h_before')
                        total_subscribers_notified += len(successfully_notified)
                        print(f"🔔 Уведомлено {len(successfully_notified)} подписчиков о матче {home_team} vs {away_team} (записано: {inserted})")
    
    if total_matches_checked > 0:
        print(f"✅ Проверено матчей в окне 2ч: {total_matches_checked}, отправлено уведомлений: {total_subscribers_notified}")


def run_once():
    now = datetime.utcnow().replace(tzinfo=UTC)
    matches = get_upcoming_matches(next_n=200, window_hours=72)
    for m in matches:
        minutes = (m["kick_off"] - now).total_seconds()/60
        if 50 <= minutes <= 70:
            lineup = get_lineups(m["id"])
            if not lineup.get("published"):
                continue
            home_stats = get_team_stats(m["home_id"])
            away_stats = get_team_stats(m["away_id"])
            odds = fetch_odds_global(m["id"])
            analysis = generate(m, home_stats, away_stats, odds)
            text = format_match_analysis(m, home_stats, away_stats, odds, analysis)
            
            # Сохраняем прогноз в базу данных
            try:
                from modules.database import save_prediction
                match_info = {
                    'match_id': str(m["id"]),
                    'home_team': m.get("home"),
                    'away_team': m.get("away"),
                    'league': m.get("competition"),
                    'match_date': m.get("kick_off"),
                    'round': m.get("matchday", "Unknown")
                }
                save_prediction(match_info, analysis, analysis.get('factors', {}))
                print(f"✅ Прогноз сохранен в БД (scheduler): {m.get('home')} vs {m.get('away')}")
            except Exception as e:
                print(f"⚠️ Не удалось сохранить прогноз в БД: {e}")
            
            # send to channel
            try:
                if CHANNEL_ID:
                    bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
            except Exception:
                pass
            # send to users
            users = load_users()
            for u in users:
                try:
                    bot.send_message(u, text, parse_mode="HTML")
                except Exception:
                    continue

def verify_results():
    """Проверяет и обновляет результаты завершенных матчей"""
    try:
        from modules.results_verifier import verify_match_results
        print("🔍 Проверяю результаты завершенных матчей...")
        stats = verify_match_results()
        print(f"✅ Проверено: {stats['total']}, Обновлено: {stats['updated']}, Ошибок: {stats['failed']}")
    except Exception as e:
        print(f"❌ Ошибка проверки результатов: {e}")


if __name__ == "__main__":
    # Сначала проверяем результаты завершенных матчей
    verify_results()
    # Отправляем уведомления подписчикам за 2 часа до матчей
    notify_subscribers()
    # Затем делаем прогнозы для предстоящих (за 50-70 минут)
    run_once()
