from statistics import mean

# 🏆 РЕЙТИНГ ЛИГ - коэффициент класса лиги
# Топ-5 лиги Европы имеют более высокий коэффициент
LEAGUE_CLASS_MULTIPLIER = {
    # Топ-5 лиги Европы
    "Premier League": 1.30,
    "La Liga": 1.30,
    "Serie A": 1.25,
    "Bundesliga": 1.25,
    "Ligue 1": 1.20,
    
    # Другие сильные европейские лиги
    "Primeira Liga": 1.10,  # Португалия
    "Eredivisie": 1.05,      # Нидерланды
    "Championship": 1.00,     # Англия 2
    "Belgian Pro League": 1.00,
    
    # Средние лиги
    "Super Lig": 0.95,       # Турция
    "Premiership": 0.90,     # Шотландия
    "Greek Super League": 0.85,  # Греция
    "Primeira Liga": 0.85,   # Кипр
    
    # Бразилия
    "Brasileiro Serie A": 1.15,
    
    # Дефолтное значение для неизвестных лиг
    "default": 1.00
}

# 🌟 ИЗВЕСТНЫЕ ТОП-КЛУБЫ И ИХ ЛИГИ
# Используется для определения класса команды в европейских турнирах
TEAM_LEAGUES = {
    # Испания (La Liga)
    "Real Madrid": "La Liga",
    "Barcelona": "La Liga",
    "Atletico Madrid": "La Liga",
    "Athletic Club": "La Liga",
    "Real Sociedad": "La Liga",
    "Villarreal": "La Liga",
    "Sevilla": "La Liga",
    "Real Betis": "La Liga",
    
    # Англия (Premier League)
    "Manchester City": "Premier League",
    "Liverpool": "Premier League",
    "Arsenal": "Premier League",
    "Manchester United": "Premier League",
    "Chelsea": "Premier League",
    "Tottenham": "Premier League",
    "Newcastle": "Premier League",
    "Aston Villa": "Premier League",
    
    # Италия (Serie A)
    "Inter": "Serie A",
    "AC Milan": "Serie A",
    "Juventus": "Serie A",
    "Napoli": "Serie A",
    "Roma": "Serie A",
    "Lazio": "Serie A",
    "Atalanta": "Serie A",
    
    # Германия (Bundesliga)
    "Bayern Munich": "Bundesliga",
    "Borussia Dortmund": "Bundesliga",
    "RB Leipzig": "Bundesliga",
    "Bayer Leverkusen": "Bundesliga",
    "Frankfurt": "Bundesliga",
    
    # Франция (Ligue 1)
    "PSG": "Ligue 1",
    "Monaco": "Ligue 1",
    "Marseille": "Ligue 1",
    "Lyon": "Ligue 1",
    "Lille": "Ligue 1",
    
    # Португалия (Primeira Liga)
    "Benfica": "Primeira Liga",
    "Porto": "Primeira Liga",
    "Sporting CP": "Primeira Liga",
    
    # Нидерланды (Eredivisie)
    "Ajax": "Eredivisie",
    "PSV": "Eredivisie",
    "Feyenoord": "Eredivisie",
    
    # Греция (Greek Super League)
    "Olympiakos Piraeus": "Greek Super League",
    "Olympiacos": "Greek Super League",
    "Panathinaikos": "Greek Super League",
    "AEK Athens": "Greek Super League",
    
    # Другие
    "Celtic": "Premiership",
    "Rangers": "Premiership",
    "Galatasaray": "Super Lig",
    "Fenerbahce": "Super Lig",
}

# ⭐ ЭЛИТНЫЕ КЛУБЫ - получают дополнительный бонус
# Это самые титулованные клубы Европы
ELITE_CLUBS = [
    "Real Madrid", "Barcelona", "Bayern Munich", "Manchester City", 
    "Liverpool", "PSG", "Inter", "AC Milan", "Juventus", 
    "Chelsea", "Manchester United", "Arsenal", "Atletico Madrid",
    "Borussia Dortmund", "Benfica", "Porto"
]


def is_elite_club(team_name):
    """
    Проверить является ли команда элитным клубом
    
    Args:
        team_name: Название команды
        
    Returns:
        bool: True если команда элитная
    """
    if not team_name:
        return False
    
    team_name_lower = team_name.lower()
    
    for elite in ELITE_CLUBS:
        if elite.lower() in team_name_lower or team_name_lower in elite.lower():
            return True
    
    return False


def get_team_league(team_name):
    """
    Определить лигу команды по её названию
    
    Args:
        team_name: Название команды
        
    Returns:
        str: Название лиги или пустая строка
    """
    if not team_name:
        return ""
    
    # Поиск команды в словаре (частичное совпадение)
    team_name_lower = team_name.lower()
    
    for team, league in TEAM_LEAGUES.items():
        if team.lower() in team_name_lower or team_name_lower in team.lower():
            return league
    
    return ""


def get_league_class_multiplier(league_name):
    """
    Получить коэффициент класса лиги
    
    Args:
        league_name: Название лиги
        
    Returns:
        float: Коэффициент от 0.85 до 1.30
    """
    if not league_name:
        return 1.0
    
    # Поиск лиги (частичное совпадение для гибкости)
    league_name_lower = league_name.lower()
    
    for league, multiplier in LEAGUE_CLASS_MULTIPLIER.items():
        if league.lower() in league_name_lower:
            return multiplier
    
    # Если лига не найдена, используем дефолтное значение
    return LEAGUE_CLASS_MULTIPLIER["default"]


def analyze_h2h_matches(h2h_matches, home_team, away_team):
    """
    Детальный анализ последних встреч между командами
    
    Args:
        h2h_matches: Список матчей H2H
        home_team: Имя команды хозяев
        away_team: Имя команды гостей
    
    Returns:
        dict: Анализ H2H с победами, ничьими, средним тоталом
    """
    if not h2h_matches:
        return {
            "home_wins": 0,
            "away_wins": 0,
            "draws": 0,
            "avg_total": 2.5,
            "h2h_factor": 1.0,
            "summary": ""
        }
    
    home_wins = 0
    away_wins = 0
    draws = 0
    total_goals = 0
    matches_count = len(h2h_matches)
    
    for match in h2h_matches:
        home_score = match.get("home_score", 0)
        away_score = match.get("away_score", 0)
        
        total_goals += home_score + away_score
        
        if home_score > away_score:
            home_wins += 1
        elif away_score > home_score:
            away_wins += 1
        else:
            draws += 1
    
    avg_total = round(total_goals / matches_count, 1) if matches_count > 0 else 2.5
    
    # H2H фактор для корректировки прогноза
    # Если команда выигрывает в большинстве встреч, она получает бонус
    if home_wins > away_wins * 2:
        h2h_factor_home = 1.15  # +15% к силе хозяев
        h2h_factor_away = 0.90  # -10% к силе гостей
    elif away_wins > home_wins * 2:
        h2h_factor_home = 0.90
        h2h_factor_away = 1.15
    else:
        h2h_factor_home = 1.0
        h2h_factor_away = 1.0
    
    summary = f"Последние {matches_count} встреч: {home_team} {home_wins}П-{draws}Н-{away_wins}П. Средний тотал: {avg_total}"
    
    return {
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "avg_total": avg_total,
        "h2h_factor_home": h2h_factor_home,
        "h2h_factor_away": h2h_factor_away,
        "summary": summary
    }


def get_tournament_importance(league_name):
    """
    Определяет важность турнира для расчета мотивации
    
    Args:
        league_name: Название турнира
    
    Returns:
        float: Множитель важности (1.0 - 1.25)
    """
    if not league_name:
        return 1.0
    
    league_lower = league_name.lower()
    
    # Еврокубки - максимальная важность
    if any(comp in league_lower for comp in ["champions league", "лига чемпионов"]):
        return 1.25  # Лига Чемпионов - самый престижный турнир
    elif any(comp in league_lower for comp in ["europa league", "лига европы"]):
        return 1.20  # Лига Европы
    elif any(comp in league_lower for comp in ["conference league", "конференц лига"]):
        return 1.15  # Конференц-лига
    
    # Международные турниры
    elif any(comp in league_lower for comp in ["world cup", "чемпионат мира"]):
        return 1.30  # ЧМ - высочайшая мотивация
    elif any(comp in league_lower for comp in ["european championship", "евро", "чемпионат европы"]):
        return 1.25  # Евро
    
    # Кубковые турниры
    elif any(comp in league_lower for comp in ["cup", "кубок", "copa"]):
        return 1.10  # Кубки - повышенная мотивация
    
    # Обычные лиги - стандартная мотивация
    return 1.0


def calculate_motivation_factor(position, total_teams=20, tournament_importance=1.0):
    """
    Рассчитывает фактор мотивации на основе положения в таблице и важности турнира
    
    Args:
        position: Позиция команды в таблице
        total_teams: Общее количество команд в лиге
        tournament_importance: Важность турнира (1.0 - 1.3)
    
    Returns:
        float: Фактор мотивации (0.9 - 1.5)
    """
    base_motivation = 1.0
    
    if position:
        # Топ-3: борьба за титул/еврокубки (+10-15%)
        if position <= 3:
            base_motivation = 1.15
        
        # 4-6 место: борьба за еврокубки (+5-10%)
        elif position <= 6:
            base_motivation = 1.10
        
        # Зона вылета (последние 3 места): отчаянная борьба (+10%)
        elif position >= total_teams - 2:
            base_motivation = 1.10
        
        # Зона опасности (4-6 с конца): повышенная мотивация (+5%)
        elif position >= total_teams - 5:
            base_motivation = 1.05
    
    # Применяем множитель важности турнира
    final_motivation = base_motivation * tournament_importance
    
    # Ограничиваем максимум
    return min(final_motivation, 1.5)


def analyze_streak(form):
    """
    Анализирует серию результатов команды
    
    Args:
        form: Строка формы (например "WWDLW")
    
    Returns:
        dict: Информация о серии и её влиянии
    """
    if not form or len(form) < 3:
        return {"streak_factor": 1.0, "description": ""}
    
    # Последние 3 матча важнее всего
    recent_3 = form[-3:]
    
    # Победная серия
    if recent_3 == "WWW":
        return {"streak_factor": 1.20, "description": "3 победы подряд! 🔥"}
    elif recent_3.count('W') >= 2 and 'L' not in recent_3:
        return {"streak_factor": 1.10, "description": "Отличная форма"}
    
    # Проигрышная серия
    elif recent_3 == "LLL":
        return {"streak_factor": 0.85, "description": "3 поражения подряд 📉"}
    elif recent_3.count('L') >= 2:
        return {"streak_factor": 0.90, "description": "Плохая форма"}
    
    # Стабильная форма
    elif 'L' not in recent_3:
        return {"streak_factor": 1.05, "description": "Стабильная форма"}
    
    return {"streak_factor": 1.0, "description": ""}


def calculate_team_strength(team_stats, is_home=False, form="", team_league="", team_name=""):
    """
    Рассчитывает силу атаки и защиты команды на основе реальной статистики
    
    Args:
        team_stats: Статистика команды из standings API
        is_home: Играет ли команда дома (для домашнего фактора)
        form: Строка формы команды (например "WWDLW")
        team_league: Название лиги команды (для учета класса лиги)
        team_name: Название команды (для определения элитных клубов)
    
    Returns:
        dict: {"attack": float, "defense": float}
    """
    print(f"\n🔍 [DEBUG calculate_team_strength] Команда: {team_name}")
    print(f"   is_home={is_home}, form={form}, league={team_league}")
    
    if not team_stats:
        # Базовые значения если нет статистики
        base_attack = 1.3 if is_home else 1.1
        base_defense = 1.2 if is_home else 1.3
        print(f"   ⚠️ Нет статистики! Используем базовые значения: attack={base_attack:.2f}, defense={base_defense:.2f}")
        return {"attack": base_attack, "defense": base_defense}
    
    # Реальные средние показатели из статистики
    played = max(team_stats.get("played", 1), 1)
    goals_for = team_stats.get("goals_for", 0)
    goals_against = team_stats.get("goals_against", 0)
    
    # Средняя атака = забитые голы за матч
    attack = goals_for / played
    # Средняя защита = пропущенные голы за матч (чем меньше, тем лучше)
    defense = goals_against / played
    
    print(f"   📊 Базовая статистика: {goals_for}GF / {goals_against}GA в {played} матчах")
    print(f"   📊 Исходные значения: attack={attack:.3f}, defense={defense:.3f}")
    
    # ⭐ ЭЛИТНЫЙ КЛУБ: умеренный бонус для топ-команд
    is_elite = is_elite_club(team_name)
    if is_elite:
        attack *= 1.12  # +12% к атаке для элиты
        defense *= 0.90  # -10% пропускаемых для элиты
        print(f"   ⭐ ЭЛИТНЫЙ КЛУБ: attack={attack:.3f} (×1.12), defense={defense:.3f} (×0.90)")
    
    # 🏠 ДОМАШНИЙ ФАКТОР: умеренное преимущество хозяев
    if is_home:
        attack *= 1.10  # +10% к атаке хозяев
        defense *= 0.95  # -5% пропускаемых хозяев
        print(f"   🏠 ДОМАШНИЙ ФАКТОР: attack={attack:.3f} (×1.10), defense={defense:.3f} (×0.95)")
    
    # 📈 УЧЕТ ФОРМЫ: последние 5 матчей
    if form and len(form) >= 3:
        wins = form.count('W')
        losses = form.count('L')
        form_length = len(form)
        
        # Form score от -1.0 до +1.0
        form_score = (wins - losses) / form_length
        
        # Применяем умеренный эффект формы
        attack_before_form = attack
        defense_before_form = defense
        attack *= (1.0 + 0.18 * form_score)  # ±18% в зависимости от формы
        defense *= (1.0 - 0.12 * form_score)  # Форма влияет на защиту меньше
        print(f"   📈 ФОРМА ({form}): score={form_score:+.2f}, attack={attack:.3f} (×{(1.0 + 0.18 * form_score):.3f}), defense={defense:.3f} (×{(1.0 - 0.12 * form_score):.3f})")
    
    # ФИНАЛЬНЫЕ ОГРАНИЧЕНИЯ для реалистичных значений
    attack_before_clamp = attack
    defense_before_clamp = defense
    attack = max(0.4, min(attack, 3.0))  # Диапазон [0.4, 3.0] - поднято для элитных команд
    defense = max(0.6, min(defense, 2.0))  # Диапазон [0.6, 2.0]
    
    if attack != attack_before_clamp or defense != defense_before_clamp:
        print(f"   ⚙️ CLAMP применен: attack {attack_before_clamp:.3f}→{attack:.3f}, defense {defense_before_clamp:.3f}→{defense:.3f}")
    
    print(f"   ✅ ИТОГО: attack={attack:.3f}, defense={defense:.3f}")
    
    return {
        "attack": attack,
        "defense": defense
    }


def generate_betting_recommendations(predictions):
    """
    Генерирует топ-3 рекомендации для ставок на основе прогноза
    
    Args:
        predictions: Словарь с прогнозами
    
    Returns:
        list: Список из 3 рекомендаций
    """
    recommendations = []
    
    # Извлекаем данные из прогноза
    expected_result = predictions.get("expected_result", "")
    total_goals_str = predictions.get("total_goals", "")
    both_to_score = predictions.get("both_to_score", "")
    home_total_str = predictions.get("home_total", "")
    away_total_str = predictions.get("away_total", "")
    
    # Парсим тотал
    try:
        total_goals = float(total_goals_str.split(":")[1].strip().split()[0])
    except:
        total_goals = 2.5
    
    # Парсим индивидуальные тоталы
    try:
        home_total = float(home_total_str.split(":")[1].strip())
    except:
        home_total = 1.5
    
    try:
        away_total = float(away_total_str.split(":")[1].strip())
    except:
        away_total = 1.5
    
    # 1. Рекомендация по результату матча
    if "Победа" in expected_result:
        recommendations.append(f"✅ {expected_result}")
    elif "Ничья" in expected_result:
        recommendations.append(f"✅ Ничья")
    else:
        recommendations.append(f"✅ {expected_result}")
    
    # 2. Рекомендация по тоталу (точные значения как в БК)
    if total_goals >= 3.2:
        recommendations.append(f"✅ Тотал больше 3.5")
    elif total_goals >= 2.7:
        recommendations.append(f"✅ Тотал больше 2.5")
    elif total_goals >= 2.2:
        recommendations.append(f"✅ Тотал больше 2")
    elif total_goals >= 1.7:
        recommendations.append(f"✅ Тотал меньше 2.5")
    elif total_goals >= 1.2:
        recommendations.append(f"✅ Тотал меньше 2")
    else:
        recommendations.append(f"✅ Тотал меньше 1.5")
    
    # 3. Рекомендация по индивидуальным тоталам или "обе забьют"
    if "Да" in both_to_score or "Скорее да" in both_to_score:
        recommendations.append(f"✅ Обе команды забьют")
    else:
        # Индивидуальный тотал самой сильной команды
        if home_total > away_total:
            team_name = expected_result.replace("Победа ", "") if "Победа" in expected_result else "Хозяева"
            if home_total >= 2.0:
                recommendations.append(f"✅ ИТ {team_name} больше 1.5")
            elif home_total >= 1.5:
                recommendations.append(f"✅ ИТ {team_name} больше 1")
            else:
                recommendations.append(f"✅ ИТ {team_name} больше 0.5")
        else:
            if away_total >= 2.0:
                recommendations.append(f"✅ ИТ гостей больше 1.5")
            elif away_total >= 1.5:
                recommendations.append(f"✅ ИТ гостей больше 1")
            else:
                recommendations.append(f"✅ ИТ гостей больше 0.5")
    
    return recommendations[:3]


def calculate_btts_probability(home_attack, away_attack, home_clean_sheets=0, away_clean_sheets=0):
    """
    Рассчитывает вероятность что обе команды забьют
    
    Args:
        home_attack: Средняя атака хозяев
        away_attack: Средняя атака гостей
        home_clean_sheets: Количество сухих матчей хозяев
        away_clean_sheets: Количество сухих матчей гостей
    
    Returns:
        str: "Да", "Скорее да", "Нет", "Скорее нет"
    """
    # Если у одной из команд очень много сухих матчей (>5), вероятность BTTS низкая
    if home_clean_sheets > 5 or away_clean_sheets > 5:
        return "Скорее нет"
    
    # Обе команды должны забить минимум 0.5 гола в среднем
    if home_attack >= 1.0 and away_attack >= 1.0:
        # Обе команды результативны
        if home_clean_sheets > 3 or away_clean_sheets > 3:
            return "Скорее да"  # Но есть надежная защита
        return "Да"
    elif home_attack >= 0.7 and away_attack >= 0.7:
        # Средняя результативность
        if home_clean_sheets > 2 or away_clean_sheets > 2:
            return "Скорее нет"
        return "Скорее да"
    else:
        # Хотя бы одна команда слабо забивает
        if home_clean_sheets > 3 or away_clean_sheets > 3:
            return "Нет"  # Усиливаем прогноз
        return "Скорее нет"


def calculate_corners_prediction(home_attack, away_attack, home_position=None, away_position=None, total_teams=20):
    """
    Умный расчет прогноза по угловым на основе силы атаки и позиции команд
    
    Логика:
    - Сильные атакующие команды бьют больше угловых
    - Команды сверху таблицы контролируют мяч -> больше угловых
    - Базовое значение: 9-11 угловых в среднем матче
    """
    # Базовое количество угловых в среднем матче
    base_corners = 10.0
    
    # Корректировка на силу атаки (0.3 - 3.5)
    # Чем сильнее атака, тем больше угловых
    attack_total = home_attack + away_attack
    attack_factor = 0.75 + (attack_total / 4.0) * 0.5  # 0.75 - 1.25
    
    # Корректировка на позицию в таблице
    position_factor = 1.0
    if home_position and away_position and total_teams:
        # Топ-команды (верхняя треть) -> больше угловых
        home_is_top = home_position <= total_teams / 3
        away_is_top = away_position <= total_teams / 3
        
        if home_is_top and away_is_top:
            position_factor = 1.2  # Два топа -> много атак и борьбы
        elif home_is_top or away_is_top:
            position_factor = 1.1  # Один топ -> выше среднего
        else:
            position_factor = 0.9  # Середняки/аутсайдеры -> меньше атак
    
    # Итоговый прогноз
    total_corners = base_corners * attack_factor * position_factor
    
    # Реалистичный диапазон: 6-14 угловых
    total_corners = max(6.0, min(14.0, total_corners))
    
    return round(total_corners, 1)


def calculate_cards_prediction(home_position=None, away_position=None, total_teams=20, home_motivation=1.0, away_motivation=1.0):
    """
    Умный расчет прогноза по желтым карточкам
    
    Логика:
    - Важные матчи (борьба за топ/против вылета) -> больше карточек
    - Высокая мотивация -> более агрессивная игра
    - Базовое значение: 3.5-4.5 ЖК в среднем матче
    """
    # Базовое количество карточек в среднем матче
    base_cards = 4.0
    
    # Фактор важности матча на основе позиции
    importance_factor = 1.0
    if home_position and away_position and total_teams:
        # Зоны важности
        top_zone = total_teams / 3  # Борьба за топ
        relegation_zone = total_teams * 2 / 3  # Борьба за выживание
        
        home_in_critical = home_position <= top_zone or home_position >= relegation_zone
        away_in_critical = away_position <= top_zone or away_position >= relegation_zone
        
        if home_in_critical and away_in_critical:
            importance_factor = 1.3  # Критичный матч для обоих -> много борьбы
        elif home_in_critical or away_in_critical:
            importance_factor = 1.15  # Критичный для одного
        else:
            importance_factor = 0.9  # Матч середняков -> спокойнее
    
    # Фактор мотивации (чем выше мотивация, тем агрессивнее игра)
    # Нейтральная мотивация (1.0) → фактор 1.0
    # Высокая мотивация (>1.0) → фактор >1.0 (больше карточек)
    # Низкая мотивация (<1.0) → фактор <1.0 (меньше карточек)
    motivation_avg = (home_motivation + away_motivation) / 2
    motivation_factor = 1.0 + (motivation_avg - 1.0) * 0.7  # 0.75 - 1.2 диапазон
    motivation_factor = max(0.75, min(1.2, motivation_factor))
    
    # Итоговый прогноз
    total_cards = base_cards * importance_factor * motivation_factor
    
    # Реалистичный диапазон: 2-7 ЖК
    total_cards = max(2.0, min(7.0, total_cards))
    
    return round(total_cards, 1)


def generate_predictions_ultra(match_data, enriched_data=None, sport_api_data=None, weather_data=None, injuries_data=None, halftime_data=None, playstyle_data=None, value_bet_data=None):
    """
    Максимально детальные прогнозы с использованием всех доступных API:
    - API-Football (базовая статистика)
    - Football-Data.org (турнирные таблицы, форма)
    - SportAPI (детальная статистика последних матчей)
    - OpenWeatherMap (погода - влияет на тотал голов)
    - Injuries API (травмы и дисквалификации)
    - Halftime stats (анализ голов по таймам)
    - Playstyle analysis (стиль игры команд)
    - Value bet analysis (сравнение с букмекерскими коэффициентами)
    """
    if not match_data:
        return {"error": "Нет данных для анализа"}

    teams = match_data.get("teams", {})
    home = teams.get("home", {}).get("name", "Home Team")
    away = teams.get("away", {}).get("name", "Away Team")
    home_id = teams.get("home", {}).get("id")
    away_id = teams.get("away", {}).get("id")
    stats = match_data.get("statistics", [])
    lineups = match_data.get("lineups", [])

    # Данные из Football-Data.org
    home_form = ""
    away_form = ""
    home_position = None
    away_position = None
    home_stats_ext = {}
    away_stats_ext = {}
    form_analysis = ""
    h2h_summary = ""
    top_scorers = []

    if enriched_data:
        home_stats_ext = enriched_data.get("home_stats", {})
        away_stats_ext = enriched_data.get("away_stats", {})
        top_scorers = enriched_data.get("top_scorers", [])
        
        if home_stats_ext:
            home_position = home_stats_ext.get("position")
            home_form = home_stats_ext.get("form", "")
            
        if away_stats_ext:
            away_position = away_stats_ext.get("position")
            away_form = away_stats_ext.get("form", "")
    
    # Определяем важность турнира для расчета мотивации
    league_info = match_data.get("league", {})
    league_name = league_info.get("name", "")
    tournament_importance = get_tournament_importance(league_name)
    
    # НОВЫЙ РАСЧЕТ: Реальные индивидуальные тоталы на основе статистики
    # Определяем лигу команды для учета класса
    home_league = get_team_league(home)
    away_league = get_team_league(away)
    
    print(f"\n📊 [HOME/AWAY STATS] Используем раздельную статистику:")
    print(f"   {home} (дома): played={home_stats_ext.get('played', 0)}, GF={home_stats_ext.get('goals_for', 0)}, GA={home_stats_ext.get('goals_against', 0)}")
    print(f"   {away} (в гостях): played={away_stats_ext.get('played', 0)}, GF={away_stats_ext.get('goals_for', 0)}, GA={away_stats_ext.get('goals_against', 0)}")
    print(f"\n🏆 [TOURNAMENT IMPORTANCE] {league_name}: importance={tournament_importance:.2f}")
    
    home_strength = calculate_team_strength(home_stats_ext, is_home=True, form=home_form, team_league=home_league, team_name=home)
    away_strength = calculate_team_strength(away_stats_ext, is_home=False, form=away_form, team_league=away_league, team_name=away)
    
    home_attack = home_strength["attack"]
    away_attack = away_strength["attack"]
    home_defense = home_strength["defense"]
    away_defense = away_strength["defense"]
    
    print(f"\n🌍 [DEBUG Cross-League Check]")
    print(f"   {home}: league={home_league}")
    print(f"   {away}: league={away_league}")
    
    # 🌍 CROSS-LEAGUE ADJUSTMENT: применяется ТОЛЬКО для межлиговых матчей
    # Для команд из одной лиги (или если лига неизвестна) не применяется
    if home_league and away_league and home_league != away_league:
        home_league_mult = get_league_class_multiplier(home_league)
        away_league_mult = get_league_class_multiplier(away_league)
        
        print(f"   🔥 МЕЖЛИГОВОЙ МАТЧ!")
        print(f"   {home_league} mult={home_league_mult:.3f}")
        print(f"   {away_league} mult={away_league_mult:.3f}")
        
        # League ratio с умеренной степенью
        league_ratio_home = (home_league_mult / away_league_mult) ** 0.6
        league_ratio_away = (away_league_mult / home_league_mult) ** 0.6
        
        print(f"   Ratio: home={league_ratio_home:.3f}, away={league_ratio_away:.3f}")
        print(f"   До adjustment: home_attack={home_attack:.3f}, home_defense={home_defense:.3f}")
        print(f"   До adjustment: away_attack={away_attack:.3f}, away_defense={away_defense:.3f}")
        
        # Применяем: attack × ratio, defense ÷ ratio
        home_attack *= league_ratio_home
        home_defense /= league_ratio_home
        away_attack *= league_ratio_away
        away_defense /= league_ratio_away
        
        print(f"   После adjustment: home_attack={home_attack:.3f}, home_defense={home_defense:.3f}")
        print(f"   После adjustment: away_attack={away_attack:.3f}, away_defense={away_defense:.3f}")
        
        # Повторный clamp после cross-league adjustment (мягче для элитных команд)
        home_attack_before = home_attack
        away_attack_before = away_attack
        home_defense_before = home_defense
        away_defense_before = away_defense
        
        home_attack = max(0.4, min(3.0, home_attack))
        away_attack = max(0.4, min(3.0, away_attack))
        home_defense = max(0.6, min(2.0, home_defense))
        away_defense = max(0.6, min(2.0, away_defense))
        
        if (home_attack != home_attack_before or away_attack != away_attack_before or 
            home_defense != home_defense_before or away_defense != away_defense_before):
            print(f"   ⚙️ Post-adjustment CLAMP:")
            if home_attack != home_attack_before:
                print(f"      home_attack {home_attack_before:.3f}→{home_attack:.3f}")
            if away_attack != away_attack_before:
                print(f"      away_attack {away_attack_before:.3f}→{away_attack:.3f}")
            if home_defense != home_defense_before:
                print(f"      home_defense {home_defense_before:.3f}→{home_defense:.3f}")
            if away_defense != away_defense_before:
                print(f"      away_defense {away_defense_before:.3f}→{away_defense:.3f}")
    else:
        print(f"   ✓ Одна лига или лиги неизвестны - cross-league adjustment НЕ применяется")
    
    # 🤖 ЗАГРУЗКА ML ВЕСОВ из многомодельной системы (15 моделей: 5 лиг × 3 алгоритма)
    ml_weights = {"h2h_weight": 1.0, "motivation_weight": 1.0, "streak_weight": 1.0}
    ml_algorithm = "default"
    
    try:
        from modules.ml_model_service import predict_weights_for_match
        
        # Подготавливаем признаки для ML модели
        match_features = {
            'position_diff': abs((home_position or 10) - (away_position or 10)),
            'home_position': float(home_position or 10),
            'away_position': float(away_position or 10),
            'home_goals_for': float(home_stats_ext.get('goals_for', 0)),
            'home_goals_against': float(home_stats_ext.get('goals_against', 0)),
            'away_goals_for': float(away_stats_ext.get('goals_for', 0)),
            'away_goals_against': float(away_stats_ext.get('goals_against', 0)),
            'home_form_wins': float(home_form.count('W') if home_form else 0),
            'away_form_wins': float(away_form.count('W') if away_form else 0),
            'home_goal_diff': float(home_stats_ext.get('goals_for', 0) - home_stats_ext.get('goals_against', 0)),
            'away_goal_diff': float(away_stats_ext.get('goals_for', 0) - away_stats_ext.get('goals_against', 0)),
            'home_points': float(home_stats_ext.get('points', 0)),
            'away_points': float(away_stats_ext.get('points', 0)),
            'points_diff': abs(float(home_stats_ext.get('points', 0) - away_stats_ext.get('points', 0))),
            'home_win_ratio': float(home_stats_ext.get('won', 0)) / max(float(home_stats_ext.get('played', 1)), 1.0),
            'away_win_ratio': float(away_stats_ext.get('won', 0)) / max(float(away_stats_ext.get('played', 1)), 1.0)
        }
        
        # Предсказываем веса используя специализированную модель для лиги
        predicted_weights = predict_weights_for_match(league_name, match_features)
        
        if predicted_weights:
            ml_weights = predicted_weights
            ml_algorithm = predicted_weights.get('algorithm', 'unknown')
            print(f"✅ Используется ML модель: {league_name}/{ml_algorithm}")
        else:
            print(f"⚠️ ML модель недоступна, используем дефолтные веса")
            
    except Exception as e:
        print(f"⚠️ Ошибка загрузки ML весов: {e}")
        # Используем дефолтные веса если модель недоступна
    
    # 🆕 АНАЛИЗ ИСТОРИИ ВСТРЕЧ (H2H)
    h2h_analysis = {"summary": "", "h2h_factor_home": 1.0, "h2h_factor_away": 1.0}
    if enriched_data:
        h2h_matches = enriched_data.get("h2h", [])
        if h2h_matches:
            h2h_analysis = analyze_h2h_matches(h2h_matches, home, away)
            h2h_summary = h2h_analysis["summary"]
    
    # ОРИГИНАЛЬНЫЕ факторы ДО применения ML весов (для сохранения в БД)
    original_h2h_factor_home = h2h_analysis.get("h2h_factor_home", 1.0)
    original_h2h_factor_away = h2h_analysis.get("h2h_factor_away", 1.0)
    
    # Применяем H2H фактор к атаке С УЧЕТОМ ML ВЕСА
    h2h_weight = ml_weights.get("h2h_weight", 1.0)
    h2h_factor_home = 1.0 + (original_h2h_factor_home - 1.0) * h2h_weight
    h2h_factor_away = 1.0 + (original_h2h_factor_away - 1.0) * h2h_weight
    
    print(f"\n🔄 [DEBUG H2H Factor]")
    print(f"   Original: home={original_h2h_factor_home:.3f}, away={original_h2h_factor_away:.3f}, ML weight={h2h_weight:.3f}")
    print(f"   Adjusted: home={h2h_factor_home:.3f}, away={h2h_factor_away:.3f}")
    print(f"   Attack до H2H: home={home_attack:.3f}, away={away_attack:.3f}")
    
    home_attack *= h2h_factor_home
    away_attack *= h2h_factor_away
    
    print(f"   Attack после H2H: home={home_attack:.3f}, away={away_attack:.3f}")
    
    # 🆕 ФАКТОР МОТИВАЦИИ на основе позиции в таблице
    # Получаем реальное количество команд из standings
    total_teams = 20  # По умолчанию
    if enriched_data and enriched_data.get("standings"):
        standings = enriched_data.get("standings", [])
        if standings:
            total_teams = len(standings)
    
    # ОРИГИНАЛЬНЫЕ факторы ДО применения ML весов
    original_home_motivation = calculate_motivation_factor(home_position, total_teams, tournament_importance)
    original_away_motivation = calculate_motivation_factor(away_position, total_teams, tournament_importance)
    
    # Применяем мотивацию с учетом ML веса
    motivation_weight = ml_weights.get("motivation_weight", 1.0)
    home_motivation_adjusted = 1.0 + (original_home_motivation - 1.0) * motivation_weight
    away_motivation_adjusted = 1.0 + (original_away_motivation - 1.0) * motivation_weight
    
    print(f"\n💪 [DEBUG Motivation Factor]")
    print(f"   Позиции: {home}={home_position}/{total_teams}, {away}={away_position}/{total_teams}")
    print(f"   Original: home={original_home_motivation:.3f}, away={original_away_motivation:.3f}, ML weight={motivation_weight:.3f}")
    print(f"   Adjusted: home={home_motivation_adjusted:.3f}, away={away_motivation_adjusted:.3f}")
    print(f"   Attack до motivation: home={home_attack:.3f}, away={away_attack:.3f}")
    
    home_attack *= home_motivation_adjusted
    away_attack *= away_motivation_adjusted
    
    print(f"   Attack после motivation: home={home_attack:.3f}, away={away_attack:.3f}")
    
    # 🆕 АНАЛИЗ СЕРИЙ (победные/проигрышные)
    home_streak = analyze_streak(home_form)
    away_streak = analyze_streak(away_form)
    
    # ОРИГИНАЛЬНЫЕ факторы ДО применения ML весов
    original_home_streak_factor = home_streak["streak_factor"]
    original_away_streak_factor = away_streak["streak_factor"]
    
    # Применяем серии с учетом ML веса
    streak_weight = ml_weights.get("streak_weight", 1.0)
    home_streak_adjusted = 1.0 + (original_home_streak_factor - 1.0) * streak_weight
    away_streak_adjusted = 1.0 + (original_away_streak_factor - 1.0) * streak_weight
    
    print(f"\n🔥 [DEBUG Streak Factor]")
    print(f"   Original: home={original_home_streak_factor:.3f}, away={original_away_streak_factor:.3f}, ML weight={streak_weight:.3f}")
    print(f"   Adjusted: home={home_streak_adjusted:.3f}, away={away_streak_adjusted:.3f}")
    print(f"   Attack до streak: home={home_attack:.3f}, away={away_attack:.3f}")
    
    home_attack *= home_streak_adjusted
    away_attack *= away_streak_adjusted
    
    print(f"   Attack после streak: home={home_attack:.3f}, away={away_attack:.3f}")
    
    # Анализ формы для текста
    form_analysis = ""
    if home_form or away_form:
        if home_streak["description"] and away_streak["description"]:
            form_analysis = f"{home}: {home_streak['description']} | {away}: {away_streak['description']}"
        elif home_streak["description"]:
            form_analysis = f"{home}: {home_streak['description']}"
        elif away_streak["description"]:
            form_analysis = f"{away}: {away_streak['description']}"
        else:
            home_wins = home_form.count('W') if home_form else 0
            away_wins = away_form.count('W') if away_form else 0
            
            if home_wins > away_wins + 1:
                form_analysis = f"{home} в отличной форме 🔥"
            elif away_wins > home_wins + 1:
                form_analysis = f"{away} в отличной форме 🔥"
            else:
                form_analysis = "Команды в сопоставимой форме"

    # Данные из SportAPI (для дополнительной точности)
    home_performance = {}
    away_performance = {}
    home_clean_sheets = 0
    away_clean_sheets = 0
    
    if sport_api_data:
        home_performance = sport_api_data.get("home_performance", {})
        away_performance = sport_api_data.get("away_performance", {})
        
        if home_performance:
            home_clean_sheets = home_performance.get("clean_sheets", 0)
            sport_home_avg = home_performance.get("avg_goals_scored", 0)
            # Небольшая корректировка на основе SportAPI (только если есть данные)
            if sport_home_avg > 0:
                home_attack = (home_attack * 0.7) + (sport_home_avg * 0.3)
            
        if away_performance:
            away_clean_sheets = away_performance.get("clean_sheets", 0)
            sport_away_avg = away_performance.get("avg_goals_scored", 0)
            if sport_away_avg > 0:
                away_attack = (away_attack * 0.7) + (sport_away_avg * 0.3)
    
    # 🆕 ФИНАЛЬНОЕ РЕАЛИСТИЧНОЕ ОГРАНИЧЕНИЕ (применяется ПОСЛЕ всех корректировок)
    # Убираем жесткий clamp - теперь используем мягкое ограничение
    MAX_REALISTIC_ATTACK = 5.0  # Увеличено для элитных команд в отличной форме
    MIN_REALISTIC_ATTACK = 0.2
    home_attack = max(MIN_REALISTIC_ATTACK, min(home_attack, MAX_REALISTIC_ATTACK))
    away_attack = max(MIN_REALISTIC_ATTACK, min(away_attack, MAX_REALISTIC_ATTACK))

    # 🎯 УМНЫЙ РАСЧЕТ УГЛОВЫХ И КАРТОЧЕК на основе статистики
    avg_corners = calculate_corners_prediction(
        home_attack, 
        away_attack, 
        home_position, 
        away_position, 
        total_teams
    )
    
    avg_cards = calculate_cards_prediction(
        home_position, 
        away_position, 
        total_teams,
        original_home_motivation,
        original_away_motivation
    )

    # Общий тотал = сумма ожидаемых голов обеих команд
    total_pred = round(home_attack + away_attack, 2)
    
    # 🌦️ УЧЕТ ПОГОДЫ (влияет на тотал голов)
    weather_adjustment = 0.0
    weather_info = ""
    if weather_data and weather_data.get("available"):
        impact = weather_data.get("impact_on_goals", "neutral")
        conditions = weather_data.get("conditions", "")
        
        if impact == "negative":
            weather_adjustment = -0.3
            weather_info = f"🌧️ Погода снижает голы: {conditions}"
        elif impact == "slight_negative":
            weather_adjustment = -0.2
            weather_info = f"☁️ Погода немного снижает голы: {conditions}"
        elif impact == "positive":
            weather_adjustment = +0.1
            weather_info = f"☀️ Идеальные условия для игры: {conditions}"
        else:
            weather_info = f"🌤️ Погода: {conditions}"
        
        # Применяем корректировку
        home_attack = max(0.2, home_attack + weather_adjustment / 2)
        away_attack = max(0.2, away_attack + weather_adjustment / 2)
        total_pred = round(home_attack + away_attack, 2)
        
        print(f"\n🌦️ [DEBUG Weather Impact]")
        print(f"   Conditions: {conditions}")
        print(f"   Impact: {impact}")
        print(f"   Adjustment: {weather_adjustment:+.2f}")
        print(f"   New total: {total_pred:.2f}")
    
    # 🏥 УЧЕТ ТРАВМ И ДИСКВАЛИФИКАЦИЙ
    injuries_home_count = 0
    injuries_away_count = 0
    injuries_info = ""
    
    if injuries_data:
        home_injuries = injuries_data.get(home_id, [])
        away_injuries = injuries_data.get(away_id, [])
        
        injuries_home_count = len(home_injuries)
        injuries_away_count = len(away_injuries)
        
        # Снижаем силу атаки за каждого травмированного (8-12% согласно архитектору)
        if injuries_home_count > 0:
            injury_penalty_home = min(0.3, injuries_home_count * 0.10)  # макс 30% снижение
            home_attack *= (1 - injury_penalty_home)
            print(f"\n🏥 [DEBUG Injuries] {home}: {injuries_home_count} травмированных, penalty={injury_penalty_home:.1%}")
        
        if injuries_away_count > 0:
            injury_penalty_away = min(0.3, injuries_away_count * 0.10)
            away_attack *= (1 - injury_penalty_away)
            print(f"🏥 [DEBUG Injuries] {away}: {injuries_away_count} травмированных, penalty={injury_penalty_away:.1%}")
        
        if injuries_home_count > 0 or injuries_away_count > 0:
            injuries_info = f"🏥 Травмы: {home} ({injuries_home_count}), {away} ({injuries_away_count})"
            total_pred = round(home_attack + away_attack, 2)
    
    # ⏱️ УЧЕТ СТАТИСТИКИ ПО ТАЙМАМ
    halftime_info = ""
    halftime_adjustment = 0.0
    if halftime_data:
        home_halftime = halftime_data.get("home", {})
        away_halftime = halftime_data.get("away", {})
        
        if home_halftime.get("available") and away_halftime.get("available"):
            home_tendency = home_halftime.get("tendency", "balanced")
            away_tendency = away_halftime.get("tendency", "balanced")
            
            # Корректировка на основе тенденций (±3-5% согласно архитектору)
            if home_tendency == "first_half" and away_tendency == "first_half":
                halftime_adjustment = +0.05  # Обе команды активны в 1-м тайме = больше голов
            elif home_tendency == "second_half" and away_tendency == "second_half":
                halftime_adjustment = +0.03  # Обе активны во 2-м тайме
            
            home_attack *= (1 + halftime_adjustment)
            away_attack *= (1 + halftime_adjustment)
            
            tendency_map = {
                "first_half": "больше голов в 1-м тайме",
                "second_half": "больше голов во 2-м тайме",
                "balanced": "равномерно по таймам"
            }
            
            halftime_info = f"⏱️ Тенденции: {home} - {tendency_map.get(home_tendency)}, {away} - {tendency_map.get(away_tendency)}"
            total_pred = round(home_attack + away_attack, 2)
            
            if halftime_adjustment > 0:
                print(f"\n⏱️ [DEBUG Halftime Adjustment] +{halftime_adjustment:.1%} к голам")
    
    # 🎯 УЧЕТ СТИЛЯ ИГРЫ
    playstyle_info = ""
    playstyle_adjustment_home = 0.0
    playstyle_adjustment_away = 0.0
    
    if playstyle_data:
        home_style = playstyle_data.get("home", {})
        away_style = playstyle_data.get("away", {})
        
        if home_style.get("available") and away_style.get("available"):
            # Агрессивные команды забивают больше (+5% согласно архитектору)
            if home_style.get("attacking_style") == "aggressive":
                playstyle_adjustment_home = 0.05
                home_attack *= (1 + playstyle_adjustment_home)
            
            if away_style.get("attacking_style") == "aggressive":
                playstyle_adjustment_away = 0.05
                away_attack *= (1 + playstyle_adjustment_away)
            
            # Possession стиль против counter стиля = больше владения, но не обязательно больше голов
            # Counter против possession = потенциал для быстрых голов
            if home_style.get("possession_style") == "possession" and away_style.get("possession_style") == "counter":
                away_attack *= 1.03  # Counter-атаки эффективнее против possession
            elif home_style.get("possession_style") == "counter" and away_style.get("possession_style") == "possession":
                home_attack *= 1.03
            
            playstyle_info = f"🎯 Стиль: {home} - {home_style.get('description')}, {away} - {away_style.get('description')}"
            total_pred = round(home_attack + away_attack, 2)
            
            print(f"\n🎯 [DEBUG Playstyle Impact]")
            print(f"   {home}: {home_style.get('description')} (adjustment={playstyle_adjustment_home:+.1%})")
            print(f"   {away}: {away_style.get('description')} (adjustment={playstyle_adjustment_away:+.1%})")
    
    # УЛУЧШЕННЫЙ прогноз "обе забьют" с использованием новой функции
    both_to_score = calculate_btts_probability(home_attack, away_attack, home_clean_sheets, away_clean_sheets)

    print(f"\n⚽ [DEBUG Expected Goals Calculation]")
    print(f"   ФИНАЛЬНЫЕ attack/defense ПЕРЕД расчетом голов:")
    print(f"   {home}: attack={home_attack:.3f}, defense={home_defense:.3f}")
    print(f"   {away}: attack={away_attack:.3f}, defense={away_defense:.3f}")
    
    # 🎯 ФОРМУЛА ОЖИДАЕМЫХ ГОЛОВ
    # Базовые значения для нормализации (исправлено 11.11.2024)
    # Архитектор: старые значения (1.45/1.05) давали +38% бонус хозяевам, что приводило к 
    # нереалистичным прогнозам (слабые команды дома побеждали топ-клубы)
    # Новые значения: 1.30/1.20 дают +8% бонус, домашнее преимущество также учитывается
    # в calculate_team_strength (attack×1.10, defense×0.95) и motivation факторе
    HOME_BASE = 1.30  # Базовое ожидание для хозяев (снижено с 1.45)
    AWAY_BASE = 1.20  # Базовое ожидание для гостей (повышено с 1.05)
    
    # Attack index: нормализованная сила атаки относительно HOME_BASE
    home_attack_index = home_attack / HOME_BASE
    away_attack_index = away_attack / HOME_BASE
    
    print(f"   Attack indexes: home={home_attack_index:.3f}, away={away_attack_index:.3f}")
    
    # Defense index: влияние защиты соперника (ограничен диапазоном 0.7-1.15)
    home_defense_index_raw = 1.25 / away_defense
    away_defense_index_raw = 1.25 / home_defense
    home_defense_index = max(0.7, min(1.15, home_defense_index_raw))
    away_defense_index = max(0.7, min(1.15, away_defense_index_raw))
    
    print(f"   Defense indexes: home={home_defense_index:.3f} (raw={home_defense_index_raw:.3f}), away={away_defense_index:.3f} (raw={away_defense_index_raw:.3f})")
    
    # Ожидаемые голы = база × attack_index × defense_index
    expected_home_goals = HOME_BASE * home_attack_index * home_defense_index
    expected_away_goals = AWAY_BASE * away_attack_index * away_defense_index
    
    print(f"   Expected goals (до clamp): home={expected_home_goals:.3f} (BASE={HOME_BASE} × {home_attack_index:.3f} × {home_defense_index:.3f})")
    print(f"   Expected goals (до clamp): away={expected_away_goals:.3f} (BASE={AWAY_BASE} × {away_attack_index:.3f} × {away_defense_index:.3f})")
    
    # Финальное ограничение для реалистичности
    expected_home_goals_before = expected_home_goals
    expected_away_goals_before = expected_away_goals
    expected_home_goals = max(0.3, min(3.0, expected_home_goals))
    expected_away_goals = max(0.3, min(3.0, expected_away_goals))
    
    if expected_home_goals != expected_home_goals_before or expected_away_goals != expected_away_goals_before:
        print(f"   ⚙️ Final clamp [0.3, 3.0]: home {expected_home_goals_before:.3f}→{expected_home_goals:.3f}, away {expected_away_goals_before:.3f}→{expected_away_goals:.3f}")
    
    # Разница ожидаемых голов определяет результат
    goals_diff = expected_home_goals - expected_away_goals
    
    print(f"\n🎯 [DEBUG Result Determination]")
    print(f"   Expected goals: {home} {expected_home_goals:.3f} - {expected_away_goals:.3f} {away}")
    print(f"   Goals difference: {goals_diff:+.3f}")
    
    # 🆕 ОБНОВЛЕННЫЕ ПОРОГИ (от Architect)
    # Победа: разница >= 0.35 гола
    # Ничья: разница <= 0.20 гола
    if goals_diff >= 0.35:
        expected_result = f"Победа {home}"
        confidence = min(95, 65 + abs(goals_diff) * 25)
        print(f"   ✅ РЕЗУЛЬТАТ: {expected_result} (diff={goals_diff:.3f} >= 0.35), confidence={confidence:.1f}%")
    elif goals_diff <= -0.35:
        expected_result = f"Победа {away}"
        confidence = min(95, 65 + abs(goals_diff) * 25)
        print(f"   ✅ РЕЗУЛЬТАТ: {expected_result} (diff={goals_diff:.3f} <= -0.35), confidence={confidence:.1f}%")
    elif abs(goals_diff) <= 0.20:
        # Очень близкие силы -> ничья
        expected_result = "Ничья"
        confidence = 60 + (0.20 - abs(goals_diff)) * 100
        print(f"   ✅ РЕЗУЛЬТАТ: {expected_result} (|diff|={abs(goals_diff):.3f} <= 0.20), confidence={confidence:.1f}%")
    else:
        # Промежуточная зона (0.20-0.35): слабая победа
        if goals_diff > 0:
            expected_result = f"Победа {home}"
        else:
            expected_result = f"Победа {away}"
        confidence = 55 + abs(goals_diff) * 25
        print(f"   ⚠️ РЕЗУЛЬТАТ: {expected_result} (промежуточная зона 0.20 < |diff|={abs(goals_diff):.3f} < 0.35), confidence={confidence:.1f}%")
    
    confidence = round(confidence, 1)

    # Финальные прогнозы с максимальной детализацией
    predictions = {
        "teams": f"{home} vs {away}",
        "total_goals": f"Тотал: {total_pred} ⚽",
        "corners": f"Угловые: {round(avg_corners, 1)} 📐",
        "cards": f"ЖК: {round(avg_cards, 1)} 🟨",
        "both_to_score": f"Обе забьют: {both_to_score}",
        "expected_result": expected_result,
        "home_total": f"ИТ {home}: {round(home_attack, 1)}",
        "away_total": f"ИТ {away}: {round(away_attack, 1)}",
        "confidence": confidence,
        "home_position": f"{home_position} место" if home_position else None,
        "away_position": f"{away_position} место" if away_position else None,
        "home_form": home_form,
        "away_form": away_form,
        "form_analysis": form_analysis,
        "h2h_summary": h2h_summary,
        "top_scorers": top_scorers,
        "home_performance": home_performance,
        "away_performance": away_performance,
        # Новые источники данных
        "weather_info": weather_info if weather_info else None,
        "injuries_info": injuries_info if injuries_info else None,
        "halftime_info": halftime_info if halftime_info else None,
        "playstyle_info": playstyle_info if playstyle_info else None,
        # Вероятности для value bet анализа
        "probabilities": {
            "home_win": round(1 / (1 + 2.718 ** (-goals_diff * 2)), 3) if goals_diff >= 0.35 else 0,
            "draw": round(1 - abs(goals_diff) / 0.35, 3) if abs(goals_diff) <= 0.20 else 0,
            "away_win": round(1 / (1 + 2.718 ** (goals_diff * 2)), 3) if goals_diff <= -0.35 else 0
        }
    }
    
    # Генерируем рекомендации для ставок
    predictions["betting_tips"] = generate_betting_recommendations(predictions)
    
    # 📈 VALUE BET АНАЛИЗ (если доступны данные)
    if value_bet_data and value_bet_data.get("has_value"):
        predictions["value_bets"] = value_bet_data.get("value_bets", [])
        print(f"\n💎 [DEBUG Value Bets Found] {len(predictions['value_bets'])} opportunities")
        for vb in predictions["value_bets"]:
            print(f"   {vb['recommendation']}: {vb['explanation']}")
    else:
        predictions["value_bets"] = []
    
    # 🆕 СОХРАНЕНИЕ ПРОГНОЗА В БАЗУ ДАННЫХ ДЛЯ ML
    try:
        from modules.database import save_prediction
        
        # Получаем веса ML модели
        from modules.database import get_ml_weights
        ml_weights = get_ml_weights()
        
        # 🎯 КРИТИЧНО: Сохраняем ОРИГИНАЛЬНЫЕ факторы ДО применения ML весов
        # Это позволяет AI анализировать чистые данные и правильно обучаться
        factors = {
            "home_attack": home_attack,  # Итоговая атака (после всех факторов)
            "away_attack": away_attack,
            "h2h_factor_home": original_h2h_factor_home,  # ОРИГИНАЛЬНЫЕ факторы
            "h2h_factor_away": original_h2h_factor_away,
            "home_motivation": original_home_motivation,
            "away_motivation": original_away_motivation,
            "home_streak_factor": original_home_streak_factor,
            "away_streak_factor": original_away_streak_factor,
            # Новые факторы для ML
            "weather_adjustment": weather_adjustment,
            "injuries_home_count": injuries_home_count,
            "injuries_away_count": injuries_away_count,
            "halftime_adjustment": halftime_adjustment,
            "playstyle_adjustment_home": playstyle_adjustment_home,
            "playstyle_adjustment_away": playstyle_adjustment_away
        }
        
        save_prediction(match_data, predictions, factors)
    except Exception as e:
        print(f"⚠️ Не удалось сохранить прогноз для ML: {e}")

    return predictions


def generate_predictions_enhanced(match_data, enriched_data=None):
    """
    Улучшенная генерация прогнозов с использованием данных из Football-Data.org
    Включает анализ формы команд, позиций в таблице, статистики H2H
    """
    if not match_data:
        return {"error": "Нет данных для анализа"}

    teams = match_data.get("teams", {})
    home = teams.get("home", {}).get("name", "Home Team")
    away = teams.get("away", {}).get("name", "Away Team")
    stats = match_data.get("statistics", [])
    lineups = match_data.get("lineups", [])

    # Анализ enriched данных из Football-Data.org
    home_form = ""
    away_form = ""
    home_position = None
    away_position = None
    home_stats_ext = {}
    away_stats_ext = {}
    form_analysis = ""
    h2h_summary = ""

    if enriched_data:
        home_stats_ext = enriched_data.get("home_stats", {})
        away_stats_ext = enriched_data.get("away_stats", {})
        
        if home_stats_ext:
            home_position = home_stats_ext.get("position")
            home_form = home_stats_ext.get("form", "")
            
        if away_stats_ext:
            away_position = away_stats_ext.get("position")
            away_form = away_stats_ext.get("form", "")
    
    # НОВЫЙ РАСЧЕТ: Реальные индивидуальные тоталы на основе статистики
    # Определяем лигу команды для учета класса
    home_league = get_team_league(home)
    away_league = get_team_league(away)
    
    home_strength = calculate_team_strength(home_stats_ext, is_home=True, form=home_form, team_league=home_league, team_name=home)
    away_strength = calculate_team_strength(away_stats_ext, is_home=False, form=away_form, team_league=away_league, team_name=away)
    
    home_attack = home_strength["attack"]
    away_attack = away_strength["attack"]
    home_defense = home_strength["defense"]
    away_defense = away_strength["defense"]
    
    # Анализ формы
    if home_form or away_form:
        home_wins = home_form.count('W') if home_form else 0
        away_wins = away_form.count('W') if away_form else 0
        
        if home_wins > away_wins + 1:
            form_analysis = f"{home} в отличной форме 🔥"
        elif away_wins > home_wins + 1:
            form_analysis = f"{away} в отличной форме 🔥"
        else:
            form_analysis = "Команды в сопоставимой форме"
    
    # H2H анализ
    if enriched_data:
        h2h_matches = enriched_data.get("h2h", [])
        if h2h_matches:
            h2h_summary = f"В последних {len(h2h_matches)} встречах"

    # Получаем количество команд в лиге для расчета мотивации
    total_teams = 20  # По умолчанию
    if enriched_data and enriched_data.get("standings"):
        standings = enriched_data.get("standings", [])
        if standings:
            total_teams = len(standings)

    # 🎯 УМНЫЙ РАСЧЕТ УГЛОВЫХ И КАРТОЧЕК на основе статистики
    avg_corners = calculate_corners_prediction(
        home_attack, 
        away_attack, 
        home_position, 
        away_position, 
        total_teams
    )
    
    # Для карточек используем мотивацию на основе позиции и важности турнира
    home_motivation = calculate_motivation_factor(home_position, total_teams, tournament_importance) if home_position else tournament_importance
    away_motivation = calculate_motivation_factor(away_position, total_teams, tournament_importance) if away_position else tournament_importance
    
    avg_cards = calculate_cards_prediction(
        home_position, 
        away_position, 
        total_teams,
        home_motivation,
        away_motivation
    )

    # Общий тотал = сумма ожидаемых голов обеих команд
    total_pred = round(home_attack + away_attack, 2)
    
    # УЛУЧШЕННЫЙ прогноз "обе забьют"
    both_to_score = calculate_btts_probability(home_attack, away_attack)
    
    probable_scorer = None

    if lineups:
        for lineup in lineups:
            start = lineup.get("startXI", [])
            if start and len(start) > 0:
                # Берем первого нападающего из состава
                striker = start[0]["player"]["name"]
                probable_scorer = striker
                break

    # 🎯 ДЕТЕРМИНИРОВАННЫЙ прогноз результата на основе СИЛЫ АТАКИ
    attack_diff = home_attack - away_attack
    
    if attack_diff > 0.5:
        expected_result = f"Победа {home}"
        confidence = min(95, 75 + abs(attack_diff) * 10)
    elif attack_diff < -0.5:
        expected_result = f"Победа {away}"
        confidence = min(95, 75 + abs(attack_diff) * 10)
    elif abs(attack_diff) <= 0.2:
        expected_result = "Ничья"
        confidence = 70 + (0.2 - abs(attack_diff)) * 50
    else:
        if attack_diff > 0:
            expected_result = f"Победа {home}"
        else:
            expected_result = f"Победа {away}"
        confidence = 70 + abs(attack_diff) * 15
    
    confidence = round(confidence, 1)

    # Получаем лучших бомбардиров лиги
    top_scorers = []
    if enriched_data:
        top_scorers = enriched_data.get("top_scorers", [])

    # Финальные прогнозы с расширенной информацией
    predictions = {
        "teams": f"{home} vs {away}",
        "total_goals": f"Тотал: {total_pred} ⚽",
        "corners": f"Угловые: {round(avg_corners, 1)} 📐",
        "cards": f"ЖК: {round(avg_cards, 1)} 🟨",
        "both_to_score": f"Обе забьют: {both_to_score}",
        "expected_result": expected_result,
        "home_total": f"ИТ {home}: {round(home_attack, 1)}",
        "away_total": f"ИТ {away}: {round(away_attack, 1)}",
        "probable_scorer": probable_scorer or "Нет ярко выраженного фаворита по голам",
        "confidence": confidence,
        "home_position": f"{home_position} место" if home_position else None,
        "away_position": f"{away_position} место" if away_position else None,
        "home_form": home_form,
        "away_form": away_form,
        "form_analysis": form_analysis,
        "h2h_summary": h2h_summary,
        "top_scorers": top_scorers
    }
    
    # Генерируем рекомендации для ставок
    predictions["betting_tips"] = generate_betting_recommendations(predictions)

    return predictions


def generate(match, home_stats, away_stats, odds):
    """
    Генерация прогнозов на основе статистики команд и коэффициентов.
    Используется в scheduler.py для автоматической рассылки.
    
    🎯 Использует детерминированную логику на основе статистики
    """
    home_name = match.get("home", "Home")
    away_name = match.get("away", "Away")
    
    # 🎯 РАСЧЕТ НА ОСНОВЕ РЕАЛЬНОЙ СТАТИСТИКИ команд
    # Используем предоставленную статистику или дефолтные значения
    home_attack = 1.5  # Базовое значение
    away_attack = 1.3  # Базовое значение
    
    # Если есть статистика команд, используем её
    if home_stats and isinstance(home_stats, dict):
        home_attack = home_stats.get("attack", 1.5)
    if away_stats and isinstance(away_stats, dict):
        away_attack = away_stats.get("attack", 1.3)
    
    # Общий тотал
    total_pred = round(home_attack + away_attack, 2)
    
    # 🎯 УМНЫЙ РАСЧЕТ УГЛОВЫХ на основе силы атаки
    avg_corners = calculate_corners_prediction(
        home_attack, 
        away_attack,
        None,  # Нет данных о позиции
        None,
        20
    )
    
    # 🎯 УМНЫЙ РАСЧЕТ КАРТОЧЕК
    avg_cards = calculate_cards_prediction(
        None,  # Нет данных о позиции
        None,
        20,
        1.0,  # Нейтральная мотивация
        1.0
    )
    
    # 🎯 ДЕТЕРМИНИРОВАННЫЙ прогноз "обе забьют"
    both_to_score = calculate_btts_probability(home_attack, away_attack, 0, 0)
    
    # 🎯 ДЕТЕРМИНИРОВАННЫЙ прогноз результата на основе СИЛЫ АТАКИ
    attack_diff = home_attack - away_attack
    
    if attack_diff > 0.5:
        expected_result = f"Победа {home_name}"
        confidence = min(95, 75 + abs(attack_diff) * 10)
    elif attack_diff < -0.5:
        expected_result = f"Победа {away_name}"
        confidence = min(95, 75 + abs(attack_diff) * 10)
    elif abs(attack_diff) <= 0.2:
        expected_result = "Ничья"
        confidence = 70 + (0.2 - abs(attack_diff)) * 50
    else:
        if attack_diff > 0:
            expected_result = f"Победа {home_name}"
        else:
            expected_result = f"Победа {away_name}"
        confidence = 70 + abs(attack_diff) * 15
    
    confidence = round(confidence, 1)
    
    predictions = {
        "teams": f"{home_name} vs {away_name}",
        "total_goals": f"Тотал: {total_pred} ⚽",
        "corners": f"Угловые: {round(avg_corners, 1)} 📐",
        "cards": f"ЖК: {round(avg_cards, 1)} 🟨",
        "both_to_score": f"Обе забьют: {both_to_score}",
        "expected_result": expected_result,
        "home_total": f"ИТ {home_name}: {round(home_attack, 1)}",
        "away_total": f"ИТ {away_name}: {round(away_attack, 1)}",
        "probable_scorer": "Нет ярко выраженного фаворита по голам",
        "confidence": confidence
    }
    
    # Генерируем рекомендации для ставок
    predictions["betting_tips"] = generate_betting_recommendations(predictions)
    
    return predictions

def generate_predictions(match_data):
    """
    Генерация прогнозов по статистике, составам и форме.
    Возвращает словарь с вероятностями и прогнозами по ключевым событиям.
    
    🎯 Использует детерминированную логику на основе статистики
    """

    if not match_data:
        return {"error": "Нет данных для анализа"}

    teams = match_data.get("teams", {})
    home = teams.get("home", {}).get("name", "Home Team")
    away = teams.get("away", {}).get("name", "Away Team")
    stats = match_data.get("statistics", [])
    lineups = match_data.get("lineups", [])

    # 🎯 БАЗОВЫЕ ЗНАЧЕНИЯ на основе средней статистики
    home_attack = 1.5  # Средняя команда
    away_attack = 1.3  # Средняя команда (гости слабее)
    
    # 🎯 УМНЫЙ РАСЧЕТ УГЛОВЫХ на основе силы атаки
    avg_corners = calculate_corners_prediction(
        home_attack, 
        away_attack,
        None,  # Нет данных о позиции
        None,
        20
    )
    
    # 🎯 УМНЫЙ РАСЧЕТ КАРТОЧЕК
    avg_cards = calculate_cards_prediction(
        None,  # Нет данных о позиции
        None,
        20,
        1.0,  # Нейтральная мотивация
        1.0
    )

    # Общий тотал = сумма ожидаемых голов
    total_pred = round(home_attack + away_attack, 2)
    
    # 🎯 ДЕТЕРМИНИРОВАННЫЙ прогноз "обе забьют"
    both_to_score = calculate_btts_probability(home_attack, away_attack, 0, 0)
    
    probable_scorer = None

    # Берем первого нападающего из состава
    if lineups:
        for lineup in lineups:
            start = lineup.get("startXI", [])
            if start and len(start) > 0:
                striker = start[0]["player"]["name"]
                probable_scorer = striker
                break

    # 🎯 ДЕТЕРМИНИРОВАННЫЙ прогноз результата на основе СИЛЫ АТАКИ
    attack_diff = home_attack - away_attack
    
    if attack_diff > 0.5:
        expected_result = f"Победа {home}"
        confidence = min(95, 75 + abs(attack_diff) * 10)
    elif attack_diff < -0.5:
        expected_result = f"Победа {away}"
        confidence = min(95, 75 + abs(attack_diff) * 10)
    elif abs(attack_diff) <= 0.2:
        expected_result = "Ничья"
        confidence = 70 + (0.2 - abs(attack_diff)) * 50
    else:
        if attack_diff > 0:
            expected_result = f"Победа {home}"
        else:
            expected_result = f"Победа {away}"
        confidence = 70 + abs(attack_diff) * 15
    
    confidence = round(confidence, 1)

    # Финальные прогнозы
    predictions = {
        "teams": f"{home} vs {away}",
        "total_goals": f"Тотал: {total_pred} ⚽",
        "corners": f"Угловые: {round(avg_corners, 1)} 📐",
        "cards": f"ЖК: {round(avg_cards, 1)} 🟨",
        "both_to_score": f"Обе забьют: {both_to_score}",
        "expected_result": expected_result,
        "home_total": f"ИТ {home}: {round(home_attack, 1)}",
        "away_total": f"ИТ {away}: {round(away_attack, 1)}",
        "probable_scorer": probable_scorer or "Нет ярко выраженного фаворита по голам",
        "confidence": confidence
    }
    
    # Генерируем рекомендации для ставок
    predictions["betting_tips"] = generate_betting_recommendations(predictions)

    return predictions
