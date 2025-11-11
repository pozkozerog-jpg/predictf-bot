import telebot
from telebot import types
from modules.data_fetcher import get_upcoming_matches, get_match_data, LEAGUES, format_round_label, search_teams, get_team_matches
from modules.predictor import generate_predictions_ultra
from modules.message_formatter import format_match_analysis
from modules.football_data_fetcher import enrich_match_data, fetch_upcoming_rounds_football_data, get_matches_from_football_data, get_match_data_from_football_data, LEAGUE_ID_TO_CODE
from modules.sport_api_fetcher import enrich_with_sport_api
from modules.database import track_user, track_action, add_subscription, remove_subscription, get_user_subscriptions, get_connection
from modules.analytics import update_excel_file
from modules.match_selector import get_top_matches, format_top_matches_message
import os
from psycopg2.extras import RealDictCursor

# Получаем токены из переменных окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is required")
bot = telebot.TeleBot(TOKEN)
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# ==================== РЕКЛАМА: НАЧАЛО ====================
# Счетчик прогнозов для каждого пользователя (для показа рекламы)
_user_prediction_count = {}

# Настройки рекламы
AD_FREQUENCY = 5  # Показывать рекламу после каждого N-го прогноза
AD_LINK = "https://lkw.cc/304c65a0"  # Ссылка на казино
AD_PROMO = "FUTY"  # Промокод

def send_advertisement(chat_id):
    """
    Отправляет рекламное сообщение пользователю
    
    ❗ КАК УПРАВЛЯТЬ РЕКЛАМОЙ:
    - Чтобы изменить частоту: измени AD_FREQUENCY (сейчас 5)
    - Чтобы изменить ссылку: измени AD_LINK
    - Чтобы изменить промокод: измени AD_PROMO
    - Чтобы отключить рекламу: закомментируй вызов check_and_send_ad()
    """
    try:
        ad_text = (
            "🎰 <b>Удвой свои выигрыши!</b>\n\n"
            f"🎁 Эксклюзивный бонус по промокоду <code>{AD_PROMO}</code>\n"
            "💰 Кэшбэк до 20% на спортивные ставки\n"
            "⚡ Мгновенный вывод средств\n\n"
            f"👉 <a href='{AD_LINK}'>Забрать бонус</a>\n\n"
            "<i>18+ | Играй ответственно</i>"
        )
        
        bot.send_message(
            chat_id,
            ad_text,
            parse_mode='HTML',
            disable_web_page_preview=False
        )
    except Exception as e:
        print(f"Ошибка отправки рекламы: {e}")

def check_and_send_ad(user_id, chat_id):
    """
    Проверяет счетчик прогнозов и отправляет рекламу при необходимости
    
    ❗ ВАЖНО: Эта функция вызывается после каждого прогноза
    Чтобы ОТКЛЮЧИТЬ рекламу полностью - удали все вызовы check_and_send_ad()
    """
    global _user_prediction_count
    
    # Увеличиваем счетчик для пользователя
    if user_id not in _user_prediction_count:
        _user_prediction_count[user_id] = 0
    
    _user_prediction_count[user_id] += 1
    
    # Если достигли нужного количества - показываем рекламу
    if _user_prediction_count[user_id] % AD_FREQUENCY == 0:
        send_advertisement(chat_id)
# ==================== РЕКЛАМА: КОНЕЦ ====================

# Словарь турниров - все на одном уровне
TOURNAMENTS = {
    "premier_league": {"label": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Премьер-лига", "league": "Premier League", "league_id": 39},
    "la_liga": {"label": "🇪🇸 Ла Лига", "league": "La Liga", "league_id": 140},
    "serie_a": {"label": "🇮🇹 Серия А", "league": "Serie A", "league_id": 135},
    "bundesliga": {"label": "🇩🇪 Бундеслига", "league": "Bundesliga", "league_id": 78},
    "ligue_1": {"label": "🇫🇷 Лига 1", "league": "Ligue 1", "league_id": 61},
    "primeira_liga": {"label": "🇵🇹 Примейра Лига", "league": "Primeira Liga", "league_id": 235},
    "eredivisie": {"label": "🇳🇱 Эредивизи", "league": "Eredivisie", "league_id": 88},
    "championship": {"label": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Чемпионшип", "league": "Championship", "league_id": 40},
    "serie_a_brazil": {"label": "🇧🇷 Бразильская Серия А", "league": "Campeonato Brasileiro Série A", "league_id": 71},
    "champions_league": {"label": "⭐ Лига Чемпионов", "league": "Champions League", "league_id": 2},
    "world_cup": {"label": "🌍 Чемпионат мира", "league": "World Cup", "league_id": 1},
    "euro": {"label": "🇪🇺 Чемпионат Европы", "league": "European Championship", "league_id": 4}
}


def analyze_bet_result(bet_tip, match_data):
    """
    Анализирует результат ставки
    
    Args:
        bet_tip: Текст ставки (например, "П1", "Тотал больше 2.5")
        match_data: Данные матча с фактическими результатами
    
    Returns:
        bool: True если ставка зашла, False если не зашла
    """
    try:
        home_goals = match_data.get('actual_home_goals')
        away_goals = match_data.get('actual_away_goals')
        actual_result = match_data.get('actual_result', '')
        
        # Если нет счета, не можем проверить
        if home_goals is None or away_goals is None:
            return False
        
        total_goals = home_goals + away_goals
        
        # П1 (победа хозяев)
        if 'П1' in bet_tip or 'победа' in bet_tip.lower() and 'хозя' in bet_tip.lower():
            return home_goals > away_goals
        
        # П2 (победа гостей)
        if 'П2' in bet_tip or 'победа' in bet_tip.lower() and 'гост' in bet_tip.lower():
            return away_goals > home_goals
        
        # Ничья
        if 'ничья' in bet_tip.lower() or 'X' == bet_tip.strip():
            return home_goals == away_goals
        
        # Тотал больше/меньше
        if 'тотал' in bet_tip.lower():
            if 'больше' in bet_tip.lower() or '>' in bet_tip:
                # Извлекаем число из ставки
                import re
                numbers = re.findall(r'\d+\.?\d*', bet_tip)
                if numbers:
                    threshold = float(numbers[0])
                    return total_goals > threshold
            elif 'меньше' in bet_tip.lower() or '<' in bet_tip:
                import re
                numbers = re.findall(r'\d+\.?\d*', bet_tip)
                if numbers:
                    threshold = float(numbers[0])
                    return total_goals < threshold
        
        # Обе забьют
        if 'обе' in bet_tip.lower() and 'забьют' in bet_tip.lower():
            if 'да' in bet_tip.lower():
                return home_goals > 0 and away_goals > 0
            elif 'нет' in bet_tip.lower():
                return home_goals == 0 or away_goals == 0
        
        # По умолчанию не можем определить
        return False
        
    except Exception as e:
        print(f"Ошибка анализа ставки: {e}")
        return False


def create_main_keyboard():
    """Создает главное меню выбора турниров"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    buttons = [
        types.InlineKeyboardButton(
            text="⭐ Топ-матчи дня",
            callback_data="top_matches"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["premier_league"]["label"],
            callback_data="league:premier_league"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["championship"]["label"],
            callback_data="league:championship"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["la_liga"]["label"],
            callback_data="league:la_liga"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["serie_a"]["label"],
            callback_data="league:serie_a"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["bundesliga"]["label"],
            callback_data="league:bundesliga"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["ligue_1"]["label"],
            callback_data="league:ligue_1"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["primeira_liga"]["label"],
            callback_data="league:primeira_liga"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["eredivisie"]["label"],
            callback_data="league:eredivisie"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["serie_a_brazil"]["label"],
            callback_data="league:serie_a_brazil"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["champions_league"]["label"],
            callback_data="league:champions_league"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["world_cup"]["label"],
            callback_data="league:world_cup"
        ),
        types.InlineKeyboardButton(
            text=TOURNAMENTS["euro"]["label"],
            callback_data="league:euro"
        )
    ]
    
    keyboard.add(*buttons)
    return keyboard


def create_round_menu(league_id):
    """Создает меню выбора раунда/тура"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    league_info = TOURNAMENTS.get(league_id)
    if not league_info:
        return None
    
    # Получаем ID лиги из API
    api_league_id = league_info.get("league_id")
    
    print(f"[DEBUG create_round_menu] league_id={league_id}, api_league_id={api_league_id}")
    
    if not api_league_id:
        print("[DEBUG create_round_menu] api_league_id is None, returning None")
        return None
    
    # Получаем доступные раунды из Football-Data.org
    rounds = fetch_upcoming_rounds_football_data(api_league_id, max_rounds=5)
    print(f"[DEBUG create_round_menu] Found {len(rounds) if rounds else 0} rounds")
    
    if not rounds:
        return None
    
    buttons = []
    for round_info in rounds:
        round_label = round_info["label"]
        round_code = round_info["code"]
        matches_count = round_info.get("matches_count", 0)
        
        button_text = f"{round_label} ({matches_count} матчей)" if matches_count > 0 else round_label
        
        buttons.append(
            types.InlineKeyboardButton(
                text=button_text,
                callback_data=f"round:{league_id}|{round_code}"
            )
        )
    
    # Кнопка "Назад" в главное меню
    buttons.append(
        types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back:main"
        )
    )
    
    keyboard.add(*buttons)
    return keyboard


def create_match_menu(league_id, round_code, api_league_id):
    """Создает меню выбора конкретного матча из раунда"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    print(f"[DEBUG create_match_menu] Getting matches for round {round_code}")
    
    # Получаем матчи раунда
    matches = get_matches_from_football_data(api_league_id, round_code)
    
    if not matches:
        print("[DEBUG create_match_menu] No matches found")
        return None
    
    print(f"[DEBUG create_match_menu] Found {len(matches)} matches")
    
    buttons = []
    for match in matches:
        home = match.get("home", "???")
        away = match.get("away", "???")
        match_id = match.get("id")
        
        button_text = f"{home} vs {away}"
        
        buttons.append(
            types.InlineKeyboardButton(
                text=button_text,
                callback_data=f"match:{league_id}|{round_code}|{match_id}"
            )
        )
    
    # Кнопка "Назад" к выбору раундов
    buttons.append(
        types.InlineKeyboardButton(
            text="⬅️ Назад к турам",
            callback_data=f"back:round|{league_id}"
        )
    )
    
    keyboard.add(*buttons)
    return keyboard


@bot.message_handler(commands=['start'])
def start(message):
    # 📊 Отслеживание пользователя
    track_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    track_action(message.from_user.id, "start", "Запуск бота")
    
    bot.send_message(
        message.chat.id,
        "⚽ <b>Футбольные прогнозы с AI-анализом</b>\n\n"
        "Анализирую матчи топ-лиг на основе реальной статистики:\n"
        "• Позиции в таблице и форма команд\n"
        "• История личных встреч (H2H)\n"
        "• Статистика последних матчей\n"
        "• 🤖 15 ML моделей (5 лиг × 3 алгоритма)\n\n"
        "📝 <b>Команды:</b>\n"
        "/analyze - Анализ матчей\n"
        "/subscribe Arsenal - Подписаться на команду 🔔\n"
        "/my_teams - Управление подписками\n"
        "/train - Обучение всех моделей (15 шт)\n"
        "/model_stats - Статистика моделей A/B\n\n"
        "Жми /analyze и выбирай матч! 🎯",
        parse_mode='HTML'
    )


@bot.message_handler(commands=['analyze'])
def analyze_command(message):
    # 📊 Отслеживание
    track_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    track_action(message.from_user.id, "analyze_start", "Начало анализа матчей")
    
    keyboard = create_main_keyboard()
    
    bot.send_message(
        message.chat.id,
        "⚽ Выберите турнир для анализа:\n\n"
        "Я соберу все доступные данные из API-Football, Football-Data.org и SportAPI "
        "для создания максимально точного прогноза!",
        reply_markup=keyboard
    )


@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Показывает статистику по прогнозам и ставкам"""
    try:
        from modules.database import get_connection
        from psycopg2.extras import RealDictCursor
        import json
        
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем ВСЕ прогнозы с результатами
        cur.execute("""
            SELECT 
                betting_tips,
                actual_home_goals,
                actual_away_goals,
                home_team,
                away_team,
                predicted_result,
                actual_result,
                result_correct
            FROM predictions
            WHERE actual_home_goals IS NOT NULL
        """)
        
        all_predictions = cur.fetchall()
        cur.close()
        conn.close()
        
        if not all_predictions:
            response = "📊 **Статистика прогнозов**\n\n"
            response += "Пока нет завершенных матчей.\n\n"
            response += "📋 **Как пополнять статистику:**\n\n"
            response += "1️⃣ Анализируйте матчи: /analyze\n"
            response += "   → Выбираете лигу → Выбираете матч\n\n"
            response += "2️⃣ Проверяйте результаты: /verify\n"
            response += "   → Обновляет результаты завершенных матчей\n\n"
            response += "3️⃣ Смотрите статистику: /stats\n"
            response += "   → Показывает точность прогнозов и ставок"
            
            bot.send_message(
                message.chat.id,
                response,
                parse_mode="Markdown"
            )
            return
        
        # Общая статистика прогнозов
        total_matches = len(all_predictions)
        correct_predictions = sum(1 for p in all_predictions if p.get('result_correct'))
        match_accuracy = round(correct_predictions / total_matches * 100, 1) if total_matches > 0 else 0
        
        # Статистика ставок (только для матчей с betting_tips)
        total_bets = 0
        won_bets = 0
        lost_bets = 0
        
        predictions_with_bets = [p for p in all_predictions if p.get('betting_tips')]
        
        for pred in predictions_with_bets:
            try:
                tips = json.loads(pred['betting_tips'])
                for tip in tips[:3]:
                    total_bets += 1
                    bet_result = analyze_bet_result(tip, pred)
                    if bet_result:
                        won_bets += 1
                    else:
                        lost_bets += 1
            except:
                pass
        
        # Формируем ответ
        response = "📊 **Статистика**\n\n"
        
        response += f"🎯 Точность прогнозов: **{match_accuracy}%** ({correct_predictions}/{total_matches})\n\n"
        
        if total_bets > 0:
            win_rate = round(won_bets / total_bets * 100, 1)
            
            response += f"💰 **Ставки:**\n"
            response += f"• ✅ Зашло: {won_bets}\n"
            response += f"• ❌ Не зашло: {lost_bets}\n"
            response += f"• 🔄 Возврат: 0\n"
            response += f"\n💡 Проходимость: **{win_rate}%** ({won_bets}/{total_bets})\n"
        else:
            response += f"💰 Ставок пока нет (старые прогнозы)\n"
        
        # Кнопка для детального просмотра
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="📋 Подробнее по турнирам",
            callback_data="stats:tournaments"
        ))
        
        bot.send_message(message.chat.id, response, reply_markup=keyboard, parse_mode="Markdown")
        track_action(message.from_user.id, "stats")
        
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Ошибка получения статистики: {e}\n\n"
            "Возможно, база данных еще не инициализирована."
        )


@bot.message_handler(commands=['verify'])
def verify_command(message):
    """Проверяет результаты завершенных матчей"""
    try:
        from modules.results_verifier import verify_match_results
        
        bot.send_message(message.chat.id, "🔍 Проверяю результаты завершенных матчей...")
        
        stats = verify_match_results()
        
        if stats['total'] == 0:
            response = "📊 **Проверка завершена**\n\n"
            response += "Нет завершенных матчей для проверки.\n\n"
            response += "💡 **Как это работает:**\n"
            response += "1. Анализируйте матчи через /analyze\n"
            response += "2. После завершения матчей запустите /verify\n"
            response += "3. Результаты обновятся автоматически\n"
            response += "4. Проверьте статистику через /stats"
        else:
            response = "📊 **Проверка результатов завершена!**\n\n"
            response += f"• Всего проверено: {stats['total']}\n"
            response += f"• ✅ Обновлено: {stats['updated']}\n"
            response += f"• ❌ Ошибок: {stats['failed']}\n"
            
            if stats['updated'] > 0:
                response += "\n💡 Теперь статистика обновлена! Проверьте /stats"
        
        bot.send_message(message.chat.id, response, parse_mode="Markdown")
        track_action(message.from_user.id, "verify")
        
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Ошибка проверки результатов: {e}"
        )


@bot.message_handler(commands=['train'])
def train_command(message):
    """Запускает обучение ML моделей (все 15 моделей: 5 лиг × 3 алгоритма)"""
    bot.send_message(message.chat.id, "🤖 Запускаю обучение всех ML моделей...\n\nЭто займет 2-5 минут (15 моделей).")
    
    try:
        from modules.multi_model_trainer import train_all_models
        
        results = train_all_models()
        
        if results:
            response = "✅ <b>Обучение завершено!</b>\n\n"
            response += f"Обучено моделей: {len(results)}\n\n"
            response += "<b>Лучшие модели по лигам:</b>\n"
            
            for result in results:
                response += f"• {result['league']}: {result['best_algorithm']} (R² = {result['accuracy']:.3f})\n"
            
            response += "\nПроверьте детали: /model_stats"
            
            bot.send_message(
                message.chat.id,
                response,
                parse_mode='HTML'
            )
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ Нет данных для обучения.\n\nДождитесь завершения матчей с прогнозами."
            )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Ошибка обучения: {e}\n\n"
            "Проверьте логи для подробностей."
        )


@bot.message_handler(commands=['model_stats'])
def model_stats_command(message):
    """Показывает статистику всех ML моделей"""
    try:
        from modules.database import get_all_model_metrics
        
        metrics = get_all_model_metrics()
        
        if not metrics:
            bot.send_message(
                message.chat.id,
                "⚠️ <b>Модели ещё не обучены</b>\n\n"
                "Запустите обучение: /train",
                parse_mode='HTML'
            )
            return
        
        # Группируем по лигам
        leagues_data = {}
        for m in metrics:
            league = m['league']
            if league not in leagues_data:
                leagues_data[league] = []
            leagues_data[league].append(m)
        
        response = "📊 <b>Статистика ML моделей</b>\n\n"
        response += f"Всего моделей: {len(metrics)}\n\n"
        
        for league, models in leagues_data.items():
            response += f"🏆 <b>{league}</b>\n"
            
            # Сортируем по точности
            sorted_models = sorted(models, key=lambda x: x['overall_accuracy'], reverse=True)
            
            for idx, model in enumerate(sorted_models):
                is_active = "✅" if model['is_active'] else "⚪"
                rank = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉"
                
                response += f"  {rank} {is_active} <b>{model['algorithm']}</b>\n"
                response += f"     Точность: {model['overall_accuracy']:.3f} | Примеров: {model['training_samples']}\n"
                response += f"     H2H: {model['h2h_r2_score']:.3f} | Мотив: {model['motivation_r2_score']:.3f} | Серия: {model['streak_r2_score']:.3f}\n"
            
            response += "\n"
        
        response += "🔄 Обновить модели: /train\n"
        response += "\n<i>✅ = активная модель для лиги</i>"
        
        # Отправляем сообщение (может быть длинным, разбиваем если нужно)
        if len(response) > 4096:
            # Разбиваем на части
            parts = []
            current_part = ""
            for line in response.split('\n'):
                if len(current_part) + len(line) + 1 > 4000:
                    parts.append(current_part)
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            if current_part:
                parts.append(current_part)
            
            for part in parts:
                bot.send_message(message.chat.id, part, parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, response, parse_mode='HTML')
            
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Ошибка получения статистики: {e}"
        )


# Throttling для inline запросов (предотвращает перегрузку API)
_inline_throttle = {}  # {user_id: {query: timestamp}}
_throttle_interval = 1.5  # секунды между запросами

@bot.inline_handler(lambda query: True)
def handle_inline_query(inline_query):
    """
    Обработчик inline запросов (@bot Arsenal)
    Показывает матчи команды (с throttling для защиты от rate limits)
    """
    query_text = inline_query.query.strip()
    user_id = inline_query.from_user.id
    
    # Throttling: игнорируем ИДЕНТИЧНЫЕ запросы в течение 1.5 секунд
    from datetime import datetime
    now = datetime.now().timestamp()
    
    if user_id in _inline_throttle:
        last_query_data = _inline_throttle[user_id]
        last_query = last_query_data.get('query', '')
        last_time = last_query_data.get('time', 0)
        
        # Блокируем только если запрос ТОЧНО такой же (не префикс!)
        if query_text == last_query and (now - last_time) < _throttle_interval:
            # Возвращаем пустой результат для идентичного запроса
            bot.answer_inline_query(inline_query.id, [], cache_time=1)
            return
    
    # Обновляем throttle данные только для запросов ≥ 3 символов
    if len(query_text) >= 3:
        _inline_throttle[user_id] = {'query': query_text, 'time': now}
    
    # Минимум 5 символов для поиска (защита от rate limits)
    if len(query_text) < 5:
        help_result = types.InlineQueryResultArticle(
            id='help',
            title='⚽ Поиск команды',
            description='Введите минимум 5 символов (например: Arsenal, Real, Bayern)',
            input_message_content=types.InputTextMessageContent(
                message_text="ℹ️ Для поиска матчей команды используйте inline режим:\n\n"
                             "@bot_name <название команды>\n\n"
                             "Примеры:\n"
                             "• @bot_name Arsenal\n"
                             "• @bot_name Real Madrid\n"
                             "• @bot_name Bayern",
                parse_mode='Markdown'
            )
        )
        bot.answer_inline_query(inline_query.id, [help_result], cache_time=300)
        return
    
    try:
        # Ищем команды по запросу
        teams = search_teams(query_text)
        
        if not teams:
            no_results = types.InlineQueryResultArticle(
                id='no_results',
                title='❌ Команды не найдены',
                description=f'По запросу "{query_text}" ничего не найдено',
                input_message_content=types.InputTextMessageContent(
                    message_text=f"❌ Команды по запросу \"{query_text}\" не найдены.\n\n"
                                 "Попробуйте изменить запрос или проверьте правильность написания.",
                    parse_mode='Markdown'
                )
            )
            bot.answer_inline_query(inline_query.id, [no_results], cache_time=60)
            return
        
        # Берем первую команду из результатов
        team = teams[0]
        team_id = team['id']
        team_name = team['name']
        country = team['country']
        
        # Получаем матчи команды
        matches = get_team_matches(team_id, days_back=7, days_ahead=30)
        
        if not matches:
            no_matches = types.InlineQueryResultArticle(
                id='no_matches',
                title=f'⚠️ {team_name}',
                description=f'Нет матчей в ближайшие 30 дней',
                input_message_content=types.InputTextMessageContent(
                    message_text=f"⚠️ **{team_name}** ({country})\n\n"
                                 f"Нет матчей в ближайшее время.",
                    parse_mode='Markdown'
                )
            )
            bot.answer_inline_query(inline_query.id, [no_matches], cache_time=300)
            return
        
        # Формируем результаты для inline режима
        results = []
        for i, match in enumerate(matches[:10]):  # Максимум 10 матчей
            match_id = match['id']
            home = match['home']
            away = match['away']
            league = match['league']
            status = match['status']
            kick_off = match['kick_off']
            
            # Определяем оппонента
            if home == team_name:
                opponent = away
                is_home = True
            else:
                opponent = home
                is_home = False
            
            # Форматируем дату
            from datetime import datetime
            try:
                date_obj = kick_off
                date_str = date_obj.strftime("%d.%m")
                time_str = date_obj.strftime("%H:%M")
            except:
                date_str = "TBD"
                time_str = ""
            
            # Получаем голы для завершенных матчей
            home_goals = match.get('home_goals', 0)
            away_goals = match.get('away_goals', 0)
            
            # Формируем title и description
            if status == 'finished':
                title = f"✅ {home} {home_goals}:{away_goals} {away}"
                description = f"{league} • {date_str}"
            elif status == 'upcoming':
                venue = "🏠" if is_home else "✈️"
                title = f"{venue} {date_str} {time_str} vs {opponent}"
                description = f"{league}"
            else:
                title = f"🔴 LIVE: {home} vs {away}"
                description = f"{league}"
            
            # Формируем message content
            if status == 'finished':
                message_text = (
                    f"✅ **Завершен**\n\n"
                    f"🏆 {league}\n"
                    f"📅 {date_str}\n\n"
                    f"**{home}** {home_goals}:{away_goals} **{away}**"
                )
            elif status == 'upcoming':
                venue_text = "Дома 🏠" if is_home else "В гостях ✈️"
                message_text = (
                    f"⚽ **{team_name}**\n"
                    f"{venue_text}\n\n"
                    f"🏆 {league}\n"
                    f"📅 {date_str} {time_str}\n\n"
                    f"**{home}** vs **{away}**\n\n"
                    f"Используйте /analyze для детального анализа"
                )
            else:
                message_text = (
                    f"🔴 **LIVE**\n\n"
                    f"🏆 {league}\n\n"
                    f"**{home}** vs **{away}**"
                )
            
            result = types.InlineQueryResultArticle(
                id=f'match_{match_id}_{i}',
                title=title,
                description=description,
                input_message_content=types.InputTextMessageContent(
                    message_text=message_text,
                    parse_mode='Markdown'
                )
            )
            results.append(result)
        
        # Отправляем результаты
        bot.answer_inline_query(
            inline_query.id, 
            results, 
            cache_time=3600,  # Кэш на 1 час (максимум для inline)
            is_personal=True
        )
        
    except Exception as e:
        print(f"[Ошибка inline запроса]: {e}")
        error_result = types.InlineQueryResultArticle(
            id='error',
            title='❌ Ошибка',
            description='Не удалось получить данные',
            input_message_content=types.InputTextMessageContent(
                message_text=f"❌ Ошибка при поиске: {e}",
                parse_mode='Markdown'
            )
        )
        bot.answer_inline_query(inline_query.id, [error_result], cache_time=10)


def handle_top_matches(call):
    """
    Обработчик кнопки "⭐ Топ-матчи дня"
    Показывает топ-5 самых интересных матчей на сегодня/завтра
    """
    bot.answer_callback_query(call.id, "Ищу самые интересные матчи...")
    
    # Отслеживание действия
    track_user(
        user_id=call.from_user.id,
        username=call.from_user.username,
        first_name=call.from_user.first_name,
        last_name=call.from_user.last_name
    )
    track_action(call.from_user.id, "top_matches", "Просмотр топ-матчей дня")
    
    try:
        # Получаем топ-матчи
        top_matches = get_top_matches(limit=5)
        
        # Форматируем сообщение
        message_text = format_top_matches_message(top_matches)
        
        # Создаем клавиатуру с кнопками для каждого матча
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = []
        
        for item in top_matches:
            match = item["match"]
            league_id = item["league_id"]
            round_code = item["round_code"]
            match_id = match.get("id")
            
            home = match.get("home", "???")
            away = match.get("away", "???")
            time = match.get("time", "")
            
            button_text = f"{home} vs {away}"
            if time:
                button_text += f" ({time})"
            
            # Используем существующий формат callback_data для совместимости с обработчиком match
            # Формат: match:{league_id}|{round_code}|{match_id}
            # league_id нужно преобразовать обратно в идентификатор из TOURNAMENTS
            league_key = None
            for key, info in TOURNAMENTS.items():
                if info.get("league_id") == league_id:
                    league_key = key
                    break
            
            if not league_key:
                continue
            
            buttons.append(
                types.InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"match:{league_key}|{round_code}|{match_id}"
                )
            )
        
        # Добавляем кнопку "Назад"
        buttons.append(
            types.InlineKeyboardButton(
                text="⬅️ Назад к выбору турнира",
                callback_data="back:main"
            )
        )
        
        keyboard.add(*buttons)
        
        # Обновляем сообщение
        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    except Exception as e:
        print(f"[Ошибка топ-матчей]: {e}")
        bot.edit_message_text(
            "⚠️ Произошла ошибка при загрузке топ-матчей.\n\n"
            "Попробуйте позже или выберите турнир вручную.",
            call.message.chat.id,
            call.message.message_id
        )


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Универсальный обработчик callback запросов"""
    
    # Обработка топ-матчей
    if call.data == "top_matches":
        handle_top_matches(call)
        return
    
    # Парсим callback data
    if ':' not in call.data:
        bot.answer_callback_query(call.id, "Ошибка формата данных")
        return
    
    action, data = call.data.split(':', 1)
    
    # Обработка кнопки "Назад"
    if action == "back":
        bot.answer_callback_query(call.id)
        
        if data == "main":
            # Возврат в главное меню
            keyboard = create_main_keyboard()
            bot.edit_message_text(
                "⚽ Выберите турнир для анализа:\n\n"
                "Я соберу все доступные данные из Football-Data.org и SportAPI "
                "для создания максимально точного прогноза!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard
            )
        elif data.startswith("round|"):
            # Возврат к выбору раундов
            league_id = data.split('|')[1]
            league_info = TOURNAMENTS.get(league_id)
            
            if league_info:
                keyboard = create_round_menu(league_id)
                if keyboard:
                    bot.edit_message_text(
                        f"{league_info['label']}\n\nВыберите тур для анализа:",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=keyboard
                    )
        return
    
    # Обработка выбора лиги
    if action == "league":
        league_id = data
        league_info = TOURNAMENTS.get(league_id)
        
        if not league_info:
            bot.answer_callback_query(call.id, "Ошибка: лига не найдена")
            return
        
        # Показываем выбор раундов для этой лиги
        bot.answer_callback_query(call.id, "Загружаю раунды...")
        keyboard = create_round_menu(league_id)
        
        if keyboard:
            bot.edit_message_text(
                f"{league_info['label']}\n\nВыберите тур для анализа:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard
            )
        else:
            # Специальное сообщение для международных турниров
            if league_id in ["world_cup", "euro"]:
                bot.edit_message_text(
                    f"😔 {league_info['label']} пока не доступен.\n\n"
                    f"Этот турнир проводится только в определенные годы. "
                    f"Попробуйте другие доступные лиги: /analyze",
                    call.message.chat.id,
                    call.message.message_id
                )
            else:
                bot.edit_message_text(
                    f"😔 К сожалению, для {league_info['label']} нет доступных предстоящих туров.",
                    call.message.chat.id,
                    call.message.message_id
                )
        return
    
    # Обработка выбора раунда - показываем список матчей
    if action == "round":
        parts = data.split('|')
        if len(parts) != 2:
            bot.answer_callback_query(call.id, "Ошибка формата данных")
            return
        
        league_id, round_code = parts
        league_info = TOURNAMENTS.get(league_id)
        
        if not league_info:
            bot.answer_callback_query(call.id, "Ошибка: лига не найдена")
            return
        
        api_league_id = league_info.get("league_id")
        
        if not api_league_id:
            bot.answer_callback_query(call.id, "Ошибка: неизвестная лига")
            return
        
        bot.answer_callback_query(call.id, "Загружаю матчи...")
        keyboard = create_match_menu(league_id, round_code, api_league_id)
        
        if keyboard:
            round_label = format_round_label(round_code)
            bot.edit_message_text(
                f"{league_info['label']}\n{round_label}\n\nВыберите матч для анализа:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard
            )
        else:
            bot.edit_message_text(
                f"😔 К сожалению, матчи не найдены для выбранного тура.",
                call.message.chat.id,
                call.message.message_id
            )
        return
    
    # Обработка выбора конкретного матча
    if action == "match":
        parts = data.split('|')
        if len(parts) != 3:
            bot.answer_callback_query(call.id, "Ошибка формата данных")
            return
        
        league_id, round_code, match_id = parts
        league_info = TOURNAMENTS.get(league_id)
        
        if not league_info:
            bot.answer_callback_query(call.id, "Ошибка: лига не найдена")
            return
        
        api_league_id = league_info.get("league_id")
        
        bot.answer_callback_query(call.id, "Анализирую матч...")
        analyze_single_match(call, match_id, api_league_id)
        return
    
    # Обработка статистики: Уровень 2 - Список турниров
    if action == "stats" and data == "tournaments":
        bot.answer_callback_query(call.id)
        from modules.database import get_tournaments_with_predictions
        
        tournaments = get_tournaments_with_predictions()
        
        if not tournaments:
            bot.edit_message_text(
                "📊 **Статистика прогнозов**\n\nПока нет завершенных матчей с прогнозами.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            return
        
        response = "📋 **Турниры с прогнозами**\n\n"
        response += "Выберите турнир для просмотра по турам:\n\n"
        
        keyboard = types.InlineKeyboardMarkup()
        for t in tournaments:
            button_text = f"{t['league'][:25]} - {t['accuracy']}% ({t['correct_predictions']}/{t['total_predictions']})"
            keyboard.add(types.InlineKeyboardButton(
                text=button_text,
                callback_data=f"stats_league:{t['league']}"
            ))
        
        keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stats:back"))
        
        bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return
    
    # Обработка статистики: Уровень 2 - Список турниров
    if action == "stats" and data == "tournaments":
        bot.answer_callback_query(call.id)
        from modules.database import get_tournaments_with_predictions
        
        tournaments = get_tournaments_with_predictions()
        
        if not tournaments:
            bot.edit_message_text(
                "📊 **Статистика прогнозов**\n\nПока нет завершенных матчей с прогнозами.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            return
        
        response = "📋 **Турниры с прогнозами**\n\nВыберите турнир:\n\n"
        
        keyboard = types.InlineKeyboardMarkup()
        for t in tournaments:
            button_text = f"{t['league']}"
            keyboard.add(types.InlineKeyboardButton(
                text=button_text,
                callback_data=f"stats_league:{t['league']}"
            ))
        
        keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stats:back"))
        
        bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return
    
    # Обработка статистики: Статистика по ставкам выбранного турнира
    if action == "stats_league":
        bot.answer_callback_query(call.id)
        from modules.database import get_predictions_by_league
        import json
        
        league_name = data
        predictions = get_predictions_by_league(league_name)
        
        if not predictions:
            bot.edit_message_text(
                f"📊 **{league_name}**\n\nНет завершенных матчей.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            return
        
        # Анализируем все ставки
        total_bets = 0
        won_bets = 0
        lost_bets = 0
        returned_bets = 0  # Возвраты (если будет логика)
        
        for pred in predictions:
            if pred.get('betting_tips'):
                try:
                    tips = json.loads(pred['betting_tips'])
                    for tip in tips[:3]:
                        total_bets += 1
                        bet_result = analyze_bet_result(tip, pred)
                        if bet_result:
                            won_bets += 1
                        else:
                            lost_bets += 1
                except:
                    pass
        
        # Вычисляем проценты
        win_rate = round(won_bets / total_bets * 100, 1) if total_bets > 0 else 0
        loss_rate = round(lost_bets / total_bets * 100, 1) if total_bets > 0 else 0
        
        # Статистика по матчам
        total_matches = len(predictions)
        correct_matches = sum(1 for p in predictions if p.get('result_correct'))
        match_accuracy = round(correct_matches / total_matches * 100, 1) if total_matches > 0 else 0
        
        response = f"📊 **{league_name}**\n\n"
        response += f"📈 **Общая статистика:**\n"
        response += f"• Всего матчей: {total_matches}\n"
        response += f"• Точность прогнозов: {match_accuracy}% ({correct_matches}/{total_matches})\n\n"
        
        response += f"💰 **Статистика ставок:**\n"
        response += f"• Всего ставок: {total_bets}\n"
        response += f"• ✅ Зашло: {won_bets} ({win_rate}%)\n"
        response += f"• ❌ Не зашло: {lost_bets} ({loss_rate}%)\n"
        
        if returned_bets > 0:
            return_rate = round(returned_bets / total_bets * 100, 1)
            response += f"• 🔄 Возврат: {returned_bets} ({return_rate}%)\n"
        
        response += f"\n💡 **Процент проходимости: {win_rate}%**\n"
        
        if total_bets == 0:
            response += "\n⚠️ Нет сохраненных ставок (старые прогнозы)"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад к турнирам", callback_data="stats:tournaments"))
        
        bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return
    
    # Обработка статистики: Детальный просмотр тура - матчи со ставками
    if action == "stats_round":
        bot.answer_callback_query(call.id)
        from modules.database import get_predictions_by_league
        import json
        
        parts = data.split('|')
        if len(parts) != 2:
            bot.answer_callback_query(call.id, "Ошибка формата данных")
            return
        
        league_name, round_number = parts
        
        # Получаем все матчи турнира и фильтруем по туру
        all_predictions = get_predictions_by_league(league_name)
        predictions = [p for p in all_predictions if p.get('round_number') == round_number]
        
        if not predictions:
            bot.edit_message_text(
                f"📊 **{league_name}**\n{round_number}\n\nНет матчей.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            return
        
        response = f"📊 **{league_name}**\n{round_number}\n\nВсего матчей: {len(predictions)}\n\n"
        
        for pred in predictions:
            emoji = "✅" if pred['result_correct'] else "❌"
            
            response += f"{emoji} **{pred['home_team']} vs {pred['away_team']}**\n"
            response += f"Прогноз: {pred['predicted_result']}\n"
            
            # Показываем фактический счет
            if pred.get('actual_home_goals') is not None and pred.get('actual_away_goals') is not None:
                response += f"Факт: {pred['actual_home_goals']}:{pred['actual_away_goals']} - {pred['actual_result']}\n"
            else:
                response += f"Факт: {pred['actual_result']}\n"
            
            # Показываем 3 ставки с результатами
            if pred.get('betting_tips'):
                try:
                    tips = json.loads(pred['betting_tips'])
                    if tips:
                        response += "\n💰 Ставки:\n"
                        
                        # Анализируем результат каждой ставки
                        for i, tip in enumerate(tips[:3], 1):
                            bet_result = analyze_bet_result(tip, pred)
                            result_emoji = "✅" if bet_result else "❌"
                            response += f"{result_emoji} {i}. {tip}\n"
                except:
                    pass
            else:
                response += "\n⚠️ Ставки не сохранены (старый прогноз)\n"
            
            response += "\n"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="⬅️ Назад к турам",
            callback_data=f"stats_league:{league_name}"
        ))
        
        bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return
    
    # Кнопка "Назад" для статистики
    if action == "stats" and data == "back":
        bot.answer_callback_query(call.id)
        stats_command(call.message)
        return


def analyze_single_match(call, match_id, api_league_id=None):
    """Анализирует один конкретный матч"""
    
    # 📊 Отслеживание анализа матча
    track_action(call.from_user.id, "analyze_match", f"Анализ матча ID: {match_id}")
    
    # Удаляем кнопки и показываем статус
    bot.edit_message_text(
        f"🔎 Анализирую матч...\n"
        f"⏳ Собираю данные из всех источников, это может занять немного времени...",
        call.message.chat.id,
        call.message.message_id
    )
    
    try:
        # Получаем данные матча из Football-Data.org
        data = get_match_data_from_football_data(match_id)
        
        if not data:
            bot.send_message(
                call.message.chat.id,
                f"😔 К сожалению, не удалось загрузить данные матча.\n\n"
                f"Попробуйте выбрать другой матч или турнир: /analyze"
            )
            return
        
        home_team = data.get("teams", {}).get("home", {}).get("name", "")
        away_team = data.get("teams", {}).get("away", {}).get("name", "")
        league = data.get("league", {}).get("name", "")
        
        # Получаем данные лиги один раз (кэширование)
        league_data_cache = {}
        if api_league_id:
            competition_code = LEAGUE_ID_TO_CODE.get(api_league_id)
            if competition_code:
                from modules.football_data_fetcher import get_standings, get_top_scorers
                try:
                    league_data_cache["standings"] = get_standings(competition_code)
                    league_data_cache["scorers"] = get_top_scorers(competition_code, limit=3)
                    print(f"[DEBUG] Cached league data for {competition_code}")
                except Exception as e:
                    print(f"[WARNING] Could not cache league data: {e}")
        
        # Собираем дополнительные данные
        if league_data_cache:
            # Извлекаем статистику команд из standings
            from modules.football_data_fetcher import get_team_stats_extended
            
            standings = league_data_cache.get("standings", [])
            
            # Получаем раздельную статистику HOME/AWAY для точных прогнозов
            home_stats = get_team_stats_extended(home_team, competition_code, venue="HOME")
            away_stats = get_team_stats_extended(away_team, competition_code, venue="AWAY")
            
            # Fallback на TOTAL если HOME/AWAY пустые
            if not home_stats or home_stats.get("played", 0) == 0:
                home_stats = get_team_stats_extended(home_team, competition_code, venue="TOTAL")
            
            if not away_stats or away_stats.get("played", 0) == 0:
                away_stats = get_team_stats_extended(away_team, competition_code, venue="TOTAL")
            
            enriched_data = {
                "standings": standings,
                "top_scorers": league_data_cache.get("scorers", []),
                "home_stats": home_stats,
                "away_stats": away_stats,
                "h2h": [],
                "form": {}
            }
        else:
            enriched_data = enrich_match_data(home_team, away_team, league)
        
        sport_api_data = {}  # Отключаем SportAPI пока нет ключа
        
        # Дополнительные факторы (учитываются в расчётах, не показываются пользователю)
        # Примечание: можно добавить когда станут доступны venue/season из API
        weather_data = None
        injuries_data = None
        halftime_data = None
        playstyle_data = None
        odds_data = None
        
        # Генерируем детальный прогноз (БЕЗ value_bet_data на первом этапе)
        analysis = generate_predictions_ultra(
            data, enriched_data, sport_api_data,
            weather_data, injuries_data, halftime_data,
            playstyle_data, None  # value_bet_data рассчитаем после прогноза
        )
        
        # Value bet анализ отключен (можно включить когда появятся данные о коэффициентах)
        
        # Сохраняем прогноз в базу данных
        try:
            from modules.database import save_prediction
            # Передаём уже существующий объект data (совместимый с API-Football форматом)
            save_prediction(data, analysis, analysis.get('factors', {}))
            print(f"✅ Прогноз сохранен в БД: {home_team} vs {away_team}")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить прогноз в БД: {e}")
        
        # Форматируем и отправляем
        text = format_match_analysis(data, analysis)
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
        
        # Отправляем в канал если задан
        if CHANNEL_ID:
            try:
                bot.send_message(CHANNEL_ID, text, parse_mode='HTML')
            except Exception:
                pass
        
        bot.send_message(
            call.message.chat.id,
            f"✅ Анализ завершен!\n\n"
            f"Хотите проанализировать другой матч? Нажмите /analyze"
        )
        
        # ==================== РЕКЛАМА: ВЫЗОВ ====================
        # Показываем рекламу 3-м сообщением после "Анализ завершен"
        check_and_send_ad(call.from_user.id, call.message.chat.id)
        # ==================== РЕКЛАМА: КОНЕЦ ====================
        
    except Exception as e:
        print(f"Ошибка при анализе матча: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(
            call.message.chat.id,
            "😔 Произошла ошибка при анализе матча. Попробуйте позже или выберите другой матч: /analyze"
        )


def analyze_tournament(call, tournament_id, leagues_filter, tournament_name=None, round_filter=None, api_league_id=None):
    """Анализирует матчи выбранного турнира/раунда"""
    
    # Определяем название турнира
    if not tournament_name:
        category = TOURNAMENTS.get(tournament_id, {})
        tournament_name = category.get("name", "турнир")
    
    # Удаляем кнопки и показываем статус
    status_text = f"🔎 Анализирую матчи: {tournament_name}\n"
    if round_filter:
        round_label = format_round_label(round_filter)
        status_text += f"📍 Раунд: {round_label}\n"
    status_text += f"⏳ Собираю данные из всех источников, это может занять немного времени..."
    
    bot.edit_message_text(
        status_text,
        call.message.chat.id,
        call.message.message_id
    )
    
    # Получаем матчи
    # Если указан раунд - используем Football-Data.org API (работает на бесплатном плане)
    if round_filter and api_league_id:
        print(f"[DEBUG analyze_tournament] Using Football-Data.org for api_league_id={api_league_id}, round={round_filter}")
        all_matches = get_matches_from_football_data(api_league_id, round_filter)
    else:
        # Без раунда - используем старый метод
        hours_to_search = 168  # 7 дней
        all_matches = get_upcoming_matches(
            hours_ahead=hours_to_search,
            league_filter=leagues_filter,
            round_filter=round_filter
        )
    
    if not all_matches:
        bot.send_message(
            call.message.chat.id,
            f"😔 К сожалению, не найдено матчей.\n\n"
            f"Попробуйте выбрать другой тур или турнир: /analyze"
        )
        return
    
    # Отправляем информацию о найденных матчах
    bot.send_message(
        call.message.chat.id,
        f"✅ Найдено матчей: {len(all_matches)}\n"
        f"📊 Анализирую первые {min(len(all_matches), 5)} матчей с полной детализацией..."
    )
    
    # Получаем данные лиги один раз (кэширование для оптимизации API запросов)
    league_data_cache = {}
    if api_league_id:
        competition_code = LEAGUE_ID_TO_CODE.get(api_league_id)
        if competition_code:
            from modules.football_data_fetcher import get_standings, get_top_scorers
            try:
                league_data_cache["standings"] = get_standings(competition_code)
                league_data_cache["scorers"] = get_top_scorers(competition_code, limit=3)
                league_data_cache["competition_code"] = competition_code
                print(f"[DEBUG] Cached league data for {competition_code}")
            except Exception as e:
                print(f"[WARNING] Could not cache league data: {e}")
    
    # Анализируем матчи (ограничиваем до 5 для производительности)
    analyzed_count = 0
    for match in all_matches[:5]:
        try:
            # Используем Football-Data.org если есть раунд, иначе API-Football
            if round_filter:
                data = get_match_data_from_football_data(match['id'])
            else:
                data = get_match_data(match['id'])
            
            if not data:
                continue
            
            home_team = data.get("teams", {}).get("home", {}).get("name", "")
            away_team = data.get("teams", {}).get("away", {}).get("name", "")
            home_team_id = data.get("teams", {}).get("home", {}).get("id")
            away_team_id = data.get("teams", {}).get("away", {}).get("id")
            league = match.get("league", "")
            match_id = match.get("id")
            
            # Собираем дополнительные данные (используем кэш если доступен)
            if league_data_cache:
                # Извлекаем статистику команд из standings
                from modules.football_data_fetcher import get_team_stats_extended
                
                competition_code = league_data_cache.get("competition_code")
                
                # Получаем раздельную статистику HOME/AWAY для точных прогнозов
                home_stats = get_team_stats_extended(home_team, competition_code, venue="HOME")
                away_stats = get_team_stats_extended(away_team, competition_code, venue="AWAY")
                
                # Fallback на TOTAL если HOME/AWAY пустые
                if not home_stats or home_stats.get("played", 0) == 0:
                    home_stats = get_team_stats_extended(home_team, competition_code, venue="TOTAL")
                
                if not away_stats or away_stats.get("played", 0) == 0:
                    away_stats = get_team_stats_extended(away_team, competition_code, venue="TOTAL")
                
                # Используем закэшированные данные
                enriched_data = {
                    "standings": league_data_cache.get("standings", []),
                    "scorers": league_data_cache.get("scorers", []),
                    "home_stats": home_stats,
                    "away_stats": away_stats,
                    "h2h": [],  # H2H требует отдельного запроса, пропускаем для оптимизации
                    "form": {}  # Form также требует запросов, пропускаем
                }
            else:
                # Используем старый метод (может превысить лимиты)
                enriched_data = enrich_match_data(home_team, away_team, league)
            
            sport_api_data = {}  # Отключаем SportAPI пока нет ключа
            
            # Генерируем детальный прогноз
            analysis = generate_predictions_ultra(data, enriched_data, sport_api_data)
            
            # Форматируем и отправляем
            text = format_match_analysis(data, analysis)
            bot.send_message(call.message.chat.id, text, parse_mode='HTML')
            
            # Отправляем в канал если задан
            if CHANNEL_ID:
                try:
                    bot.send_message(CHANNEL_ID, text, parse_mode='HTML')
                except Exception:
                    pass
            
            # ==================== РЕКЛАМА: ВЫЗОВ ====================
            # Показываем рекламу 3-м сообщением после прогноза
            check_and_send_ad(call.from_user.id, call.message.chat.id)
            # ==================== РЕКЛАМА: КОНЕЦ ====================
            
            analyzed_count += 1
            
        except Exception as e:
            print(f"Ошибка при анализе матча: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if analyzed_count > 0:
        bot.send_message(
            call.message.chat.id,
            f"✅ Анализ завершен! Обработано матчей: {analyzed_count}\n\n"
            f"Хотите проанализировать другой турнир? Нажмите /analyze"
        )
    else:
        bot.send_message(
            call.message.chat.id,
            "😔 Не удалось проанализировать матчи. Попробуйте позже или выберите другой турнир: /analyze"
        )


def get_all_teams_by_league():
    """Получить список всех команд, сгруппированных по лигам"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT DISTINCT 
                competition_name,
                home_team as team_name
            FROM historical_matches
            WHERE season = '2025'
              AND competition_name IN ('Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1')
            
            UNION
            
            SELECT DISTINCT 
                competition_name,
                away_team as team_name
            FROM historical_matches
            WHERE season = '2025'
              AND competition_name IN ('Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1')
            
            ORDER BY competition_name, team_name
        """)
        
        teams = cur.fetchall()
        
        # Группируем по лигам
        leagues_map = {}
        for row in teams:
            league = row['competition_name']
            team = row['team_name']
            if league not in leagues_map:
                leagues_map[league] = []
            if team not in leagues_map[league]:
                leagues_map[league].append(team)
        
        return leagues_map
    except Exception as e:
        print(f"❌ Ошибка получения команд: {e}")
        return {}
    finally:
        cur.close()
        conn.close()


@bot.message_handler(commands=['subscribe'])
def subscribe_command(message):
    """Подписка на команду"""
    user_id = message.from_user.id
    
    # Получаем название команды из текста
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(
            message.chat.id,
            "⚠️ Укажите название команды!\n\n"
            "Пример: <code>/subscribe Arsenal</code>\n\n"
            "Доступные лиги: Premier League, La Liga, Bundesliga, Serie A, Ligue 1",
            parse_mode='HTML'
        )
        return
    
    team_name = parts[1].strip()
    
    # Добавляем подписку
    success = add_subscription(user_id, team_name)
    
    if success:
        bot.send_message(
            message.chat.id,
            f"✅ Вы подписались на <b>{team_name}</b>!\n\n"
            f"Вы получите уведомление за 2 часа до матчей этой команды.\n\n"
            f"Управление подписками: /my_teams",
            parse_mode='HTML'
        )
    else:
        bot.send_message(
            message.chat.id,
            f"⚠️ Не удалось подписаться на <b>{team_name}</b>\n\n"
            f"Возможно, вы уже подписаны или название указано неверно.\n\n"
            f"Проверьте список подписок: /my_teams",
            parse_mode='HTML'
        )


@bot.message_handler(commands=['unsubscribe'])
def unsubscribe_command(message):
    """Отписка от команды"""
    user_id = message.from_user.id
    
    # Получаем название команды из текста
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(
            message.chat.id,
            "⚠️ Укажите название команды!\n\n"
            "Пример: <code>/unsubscribe Arsenal</code>\n\n"
            "Ваши подписки: /my_teams",
            parse_mode='HTML'
        )
        return
    
    team_name = parts[1].strip()
    
    # Удаляем подписку
    success = remove_subscription(user_id, team_name)
    
    if success:
        bot.send_message(
            message.chat.id,
            f"✅ Вы отписались от <b>{team_name}</b>\n\n"
            f"Управление подписками: /my_teams",
            parse_mode='HTML'
        )
    else:
        bot.send_message(
            message.chat.id,
            f"⚠️ Не удалось отписаться от <b>{team_name}</b>\n\n"
            f"Возможно, вы не были подписаны на эту команду.\n\n"
            f"Проверьте список подписок: /my_teams",
            parse_mode='HTML'
        )


@bot.message_handler(commands=['my_teams'])
def my_teams_command(message):
    """Управление подписками на команды"""
    user_id = message.from_user.id
    
    # Получаем текущие подписки
    subscriptions = get_user_subscriptions(user_id)
    
    if subscriptions:
        text = "🔔 <b>Ваши подписки:</b>\n\n"
        for sub in subscriptions:
            text += f"⚽ {sub['team_name']}\n"
        text += "\n<i>Вы получите уведомление за 2 часа до матча этих команд</i>\n\n"
        text += "📝 <b>Как управлять:</b>\n"
        text += "• <code>/subscribe Arsenal</code> - подписаться\n"
        text += "• <code>/unsubscribe Arsenal</code> - отписаться\n"
    else:
        text = ("🔔 <b>У вас пока нет подписок</b>\n\n"
                "Подпишитесь на любимые команды и получайте уведомления "
                "за 2 часа до их матчей!\n\n"
                "📝 <b>Как подписаться:</b>\n"
                "Используйте команду: <code>/subscribe Название</code>\n\n"
                "Примеры:\n"
                "• <code>/subscribe Arsenal</code>\n"
                "• <code>/subscribe Liverpool</code>\n"
                "• <code>/subscribe Barcelona</code>\n\n"
                "⚠️ <b>Важно:</b> Название на английском, как в базе данных\n"
                "Доступные лиги: Premier League, La Liga, Bundesliga, Serie A, Ligue 1")
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')


# Обработчик callback для подписок
@bot.callback_query_handler(func=lambda call: call.data.startswith('subscribe:') or call.data.startswith('unsub:') or call.data.startswith('subleague:') or call.data.startswith('subteam:'))
def subscription_callback(call):
    """Обработка callback для подписок"""
    user_id = call.from_user.id
    
    try:
        if call.data == "subscribe:menu":
            # Показываем меню выбора лиги
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                types.InlineKeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", callback_data="subleague:Premier League"),
                types.InlineKeyboardButton("🇪🇸 La Liga", callback_data="subleague:La Liga"),
                types.InlineKeyboardButton("🇩🇪 Bundesliga", callback_data="subleague:Bundesliga"),
                types.InlineKeyboardButton("🇮🇹 Serie A", callback_data="subleague:Serie A"),
                types.InlineKeyboardButton("🇫🇷 Ligue 1", callback_data="subleague:Ligue 1"),
                types.InlineKeyboardButton("« Назад", callback_data="subscribe:back")
            )
            bot.edit_message_text(
                "🏆 <b>Выберите лигу:</b>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        
        elif call.data.startswith("subleague:"):
            # Показываем команды лиги
            league = call.data.replace("subleague:", "")
            teams_by_league = get_all_teams_by_league()
            teams = teams_by_league.get(league, [])
            
            if not teams:
                bot.answer_callback_query(call.id, "❌ Команды не найдены")
                return
            
            # Создаем меню с командами (по 2 в ряду для компактности)
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            buttons = []
            for team in sorted(teams):
                buttons.append(
                    types.InlineKeyboardButton(
                        team,
                        callback_data=f"subteam:{team}"
                    )
                )
            keyboard.add(*buttons)
            keyboard.add(
                types.InlineKeyboardButton("« Назад к лигам", callback_data="subscribe:menu")
            )
            
            bot.edit_message_text(
                f"⚽ <b>{league}</b>\n\nВыберите команду:",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        
        elif call.data.startswith("subteam:"):
            # Подписываем на команду
            team = call.data.replace("subteam:", "")
            added = add_subscription(user_id, team)
            
            if added:
                bot.answer_callback_query(
                    call.id,
                    f"✅ Подписка на {team} оформлена!",
                    show_alert=True
                )
                # Возвращаем к главному меню подписок
                my_teams_command(call.message)
            else:
                bot.answer_callback_query(
                    call.id,
                    f"⚠️ Вы уже подписаны на {team}",
                    show_alert=True
                )
        
        elif call.data.startswith("unsub:"):
            # Отписываемся от команды
            team = call.data.replace("unsub:", "")
            removed = remove_subscription(user_id, team)
            
            if removed:
                bot.answer_callback_query(
                    call.id,
                    f"✅ Отписка от {team} выполнена",
                    show_alert=True
                )
                # Обновляем список подписок
                subscriptions = get_user_subscriptions(user_id)
                
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                
                if subscriptions:
                    text = "🔔 <b>Ваши подписки:</b>\n\n"
                    for sub in subscriptions:
                        text += f"⚽ {sub['team_name']}\n"
                        keyboard.add(
                            types.InlineKeyboardButton(
                                text=f"❌ {sub['team_name']}",
                                callback_data=f"unsub:{sub['team_name']}"
                            )
                        )
                    text += "\n<i>Вы получите уведомление за 2 часа до матча этих команд</i>\n\n"
                    keyboard.add(
                        types.InlineKeyboardButton(
                            text="➕ Добавить команду",
                            callback_data="subscribe:menu"
                        )
                    )
                else:
                    text = ("🔔 <b>У вас больше нет подписок</b>\n\n"
                            "Подпишитесь на любимые команды!\n\n")
                    keyboard.add(
                        types.InlineKeyboardButton(
                            text="➕ Подписаться на команду",
                            callback_data="subscribe:menu"
                        )
                    )
                
                bot.edit_message_text(
                    text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка отписки")
        
        elif call.data == "subscribe:back":
            # Возврат к главному меню подписок
            my_teams_command(call.message)
    
    except Exception as e:
        print(f"❌ Ошибка обработки подписки: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


bot.polling(none_stop=True)
