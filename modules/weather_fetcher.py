"""
Модуль для получения погодных данных через OpenWeatherMap API
Погода влияет на тотал голов:
- Дождь/снег снижает количество голов
- Сильный ветер влияет на точность передач и ударов
- Экстремальная жара/холод снижает интенсивность игры
"""
import os
import requests
from datetime import datetime
import pytz

API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEO_URL = "http://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/forecast"


def _geocode_location(city_name, country_code=None):
    """
    Преобразует название города в координаты
    
    Args:
        city_name: Название города (например, "London", "Manchester")
        country_code: Код страны ISO 3166 (например, "GB", "ES", "IT")
    
    Returns:
        dict: {"lat": float, "lon": float, "name": str} или None
    """
    if not API_KEY:
        print("[Weather] OPENWEATHER_API_KEY не найден")
        return None
    
    try:
        query = f"{city_name},{country_code}" if country_code else city_name
        
        params = {
            "q": query,
            "limit": 1,
            "appid": API_KEY
        }
        
        response = requests.get(GEO_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data and len(data) > 0:
            location = data[0]
            return {
                "lat": location["lat"],
                "lon": location["lon"],
                "name": location["name"],
                "country": location.get("country", "")
            }
        
        return None
    
    except Exception as e:
        print(f"[Weather Geocoding Error] {city_name}: {e}")
        return None


def get_weather_forecast(city_name, country_code=None, match_datetime=None):
    """
    Получает прогноз погоды для матча
    
    Args:
        city_name: Название города где проходит матч
        country_code: Код страны (опционально)
        match_datetime: Дата и время матча (datetime object)
    
    Returns:
        dict: {
            "temperature": float,  # Температура в °C
            "feels_like": float,   # Ощущается как
            "description": str,    # Описание (clear sky, rain, snow, etc.)
            "humidity": int,       # Влажность %
            "wind_speed": float,   # Скорость ветра м/с
            "rain": bool,          # Дождь ожидается
            "snow": bool,          # Снег ожидается
            "conditions": str,     # Интерпретация для бота
            "impact_on_goals": str # Влияние на количество голов
        }
    """
    if not API_KEY:
        return {
            "available": False,
            "error": "OPENWEATHER_API_KEY не найден"
        }
    
    try:
        # Получаем координаты
        location = _geocode_location(city_name, country_code)
        
        if not location:
            return {
                "available": False,
                "error": f"Город {city_name} не найден"
            }
        
        # Получаем прогноз погоды
        params = {
            "lat": location["lat"],
            "lon": location["lon"],
            "appid": API_KEY,
            "units": "metric",  # Celsius
            "lang": "ru"
        }
        
        response = requests.get(WEATHER_URL, params=params, timeout=10)
        response.raise_for_status()
        
        forecast_data = response.json()
        
        # Находим прогноз, ближайший к времени матча
        if match_datetime:
            # Убираем timezone для корректного сравнения (если есть)
            if match_datetime.tzinfo is not None:
                match_datetime = match_datetime.replace(tzinfo=None)
            
            closest_forecast = None
            min_time_diff = float('inf')
            
            for item in forecast_data.get("list", []):
                # Создаем UTC-aware datetime из timestamp
                forecast_time = datetime.utcfromtimestamp(item["dt"])
                time_diff = abs((forecast_time - match_datetime).total_seconds())
                
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_forecast = item
        else:
            # Если время матча не указано, берем первый прогноз
            closest_forecast = forecast_data.get("list", [{}])[0]
        
        if not closest_forecast:
            return {
                "available": False,
                "error": "Прогноз не найден"
            }
        
        # Извлекаем данные
        main = closest_forecast.get("main", {})
        weather = closest_forecast.get("weather", [{}])[0]
        wind = closest_forecast.get("wind", {})
        
        temperature = main.get("temp", 0)
        feels_like = main.get("feels_like", 0)
        description = weather.get("description", "").lower()
        humidity = main.get("humidity", 0)
        wind_speed = wind.get("speed", 0)
        
        # Проверяем осадки
        rain = "rain" in description or "drizzle" in description
        snow = "snow" in description
        
        # Анализируем условия
        conditions = _analyze_conditions(temperature, description, wind_speed, rain, snow)
        impact = _analyze_impact_on_goals(temperature, description, wind_speed, rain, snow)
        
        return {
            "available": True,
            "city": location["name"],
            "country": location["country"],
            "temperature": round(temperature, 1),
            "feels_like": round(feels_like, 1),
            "description": description,
            "humidity": humidity,
            "wind_speed": round(wind_speed, 1),
            "rain": rain,
            "snow": snow,
            "conditions": conditions,
            "impact_on_goals": impact
        }
    
    except Exception as e:
        print(f"[Weather Forecast Error] {city_name}: {e}")
        return {
            "available": False,
            "error": str(e)
        }


def _analyze_conditions(temperature, description, wind_speed, rain, snow):
    """Анализирует погодные условия для отображения пользователю"""
    conditions = []
    
    # Температура
    if temperature < 0:
        conditions.append("❄️ Мороз")
    elif temperature < 10:
        conditions.append("🌡️ Холодно")
    elif temperature > 30:
        conditions.append("🔥 Жара")
    else:
        conditions.append("✅ Комфортная температура")
    
    # Осадки
    if snow:
        conditions.append("❄️ Снег")
    elif rain:
        conditions.append("🌧️ Дождь")
    elif "clear" in description:
        conditions.append("☀️ Ясно")
    elif "cloud" in description:
        conditions.append("☁️ Облачно")
    
    # Ветер
    if wind_speed > 10:
        conditions.append("💨 Сильный ветер")
    elif wind_speed > 5:
        conditions.append("🌬️ Ветрено")
    
    return ", ".join(conditions)


def _analyze_impact_on_goals(temperature, description, wind_speed, rain, snow):
    """
    Анализирует влияние погоды на количество голов
    
    Факторы снижающие голы:
    - Дождь/снег (сложнее контролировать мяч)
    - Сильный ветер (непредсказуемость траектории)
    - Экстремальная температура (снижает интенсивность)
    
    Факторы увеличивающие голы:
    - Идеальная температура + ясно = высокая интенсивность игры
    
    Returns:
        str: "positive" (больше голов), "neutral", "slight_negative", "negative" (меньше голов)
    """
    negative_factors = 0
    positive_factors = 0
    
    # Осадки - сильно влияют
    if snow:
        negative_factors += 2
    elif rain:
        negative_factors += 1
    
    # Ветер
    if wind_speed > 10:
        negative_factors += 2
    elif wind_speed > 7:
        negative_factors += 1
    
    # Экстремальная температура
    if temperature < -5 or temperature > 35:
        negative_factors += 2
    elif temperature < 5 or temperature > 30:
        negative_factors += 1
    
    # Идеальные условия (комфортная температура + ясно + нет ветра)
    if 15 <= temperature <= 25 and "clear" in description and wind_speed < 5:
        positive_factors += 1
    
    if negative_factors >= 3:
        return "negative"  # Явно меньше голов (-0.3 от expected)
    elif negative_factors >= 1:
        return "slight_negative"  # Немного меньше голов (-0.2 от expected)
    elif positive_factors >= 1:
        return "positive"  # Немного больше голов (+0.1 от expected)
    else:
        return "neutral"  # Погода не влияет


# Карта стадионов для популярных клубов
# Используется для автоматического определения города по команде
STADIUM_LOCATIONS = {
    # Англия
    "Arsenal": ("London", "GB"),
    "Chelsea": ("London", "GB"),
    "Tottenham": ("London", "GB"),
    "West Ham": ("London", "GB"),
    "Crystal Palace": ("London", "GB"),
    "Fulham": ("London", "GB"),
    "Brentford": ("London", "GB"),
    "Manchester United": ("Manchester", "GB"),
    "Manchester City": ("Manchester", "GB"),
    "Liverpool": ("Liverpool", "GB"),
    "Everton": ("Liverpool", "GB"),
    "Newcastle": ("Newcastle", "GB"),
    "Aston Villa": ("Birmingham", "GB"),
    "Leicester": ("Leicester", "GB"),
    "Brighton": ("Brighton", "GB"),
    "Southampton": ("Southampton", "GB"),
    "Bournemouth": ("Bournemouth", "GB"),
    "Nottingham Forest": ("Nottingham", "GB"),
    "Leeds": ("Leeds", "GB"),
    "Wolves": ("Wolverhampton", "GB"),
    
    # Испания
    "Real Madrid": ("Madrid", "ES"),
    "Atletico Madrid": ("Madrid", "ES"),
    "Barcelona": ("Barcelona", "ES"),
    "Sevilla": ("Sevilla", "ES"),
    "Valencia": ("Valencia", "ES"),
    "Villarreal": ("Villarreal", "ES"),
    "Athletic Club": ("Bilbao", "ES"),
    "Real Sociedad": ("San Sebastian", "ES"),
    "Real Betis": ("Sevilla", "ES"),
    
    # Италия
    "Juventus": ("Turin", "IT"),
    "Inter": ("Milan", "IT"),
    "AC Milan": ("Milan", "IT"),
    "Napoli": ("Naples", "IT"),
    "Roma": ("Rome", "IT"),
    "Lazio": ("Rome", "IT"),
    "Atalanta": ("Bergamo", "IT"),
    "Fiorentina": ("Florence", "IT"),
    
    # Германия
    "Bayern Munich": ("Munich", "DE"),
    "Borussia Dortmund": ("Dortmund", "DE"),
    "RB Leipzig": ("Leipzig", "DE"),
    "Bayer Leverkusen": ("Leverkusen", "DE"),
    "Frankfurt": ("Frankfurt", "DE"),
    
    # Франция
    "PSG": ("Paris", "FR"),
    "Marseille": ("Marseille", "FR"),
    "Lyon": ("Lyon", "FR"),
    "Monaco": ("Monaco", "MC"),
    "Lille": ("Lille", "FR"),
}


def get_weather_for_match(home_team, away_team=None, match_datetime=None, venue_city=None):
    """
    Автоматически получает погоду для матча
    
    Args:
        home_team: Название домашней команды
        away_team: Название гостевой команды (опционально)
        match_datetime: Время матча (datetime object)
        venue_city: Город стадиона (опционально, если None - автоопределение)
    
    Returns:
        dict: Данные о погоде
    """
    # Пытаемся определить город
    if venue_city:
        city, country = venue_city, None
    elif home_team in STADIUM_LOCATIONS:
        city, country = STADIUM_LOCATIONS[home_team]
    else:
        # Не знаем где играют - возвращаем недоступность
        return {
            "available": False,
            "error": f"Город для команды '{home_team}' не найден"
        }
    
    return get_weather_forecast(city, country, match_datetime)
