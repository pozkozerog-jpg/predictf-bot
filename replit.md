# Football Predictor Bot

## Overview
This self-learning Telegram bot provides data-driven football predictions using statistics from Football-Data.org and API-Football. It leverages a multi-model machine learning system (15 models across 5 leagues) to continuously improve accuracy by learning from real match results. The bot offers features like detailed match analysis, smart round detection, inline search, "Top Matches of the Day," and team subscriptions for 12 tournaments, including top European leagues, Champions League, and World Cup. The project's ambition is to deliver highly accurate, continuously improving football predictions without external API costs for ML.

## User Preferences
I prefer that the agent removes all random numbers from all predictions, ensuring deterministic logic based purely on statistics. The agent should ensure that identical data always results in identical predictions. It should correctly apply ML weights using the formula `1 + (factor - 1) * weight`. The system should continuously learn by analyzing historical data even without new results and ensure that AI receives clean, unpolluted factors for accurate pattern analysis.

## System Architecture

**UI/UX Decisions:**
- **Simplified Navigation:** A three-level interactive menu (`/analyze` -> League -> Round -> Match) for direct access.
- **Detailed Match Analysis:** Users can select individual matches for in-depth analysis.
- **Smart Round Detection:** Bot intelligently identifies and displays upcoming rounds.
- **Inline Mode:** Search for team matches directly from any chat using `@bot_name <team>`.
- **"Top Matches of the Day":** Automatically selects interesting matches based on league class, top clubs, and derby status.
- **Team Subscriptions:** Users subscribe via `/my_teams` and receive notifications 2 hours before matches. Subscriptions are managed through simple text commands like `/subscribe Arsenal`.

**Technical Implementations & Feature Specifications:**
- **Multi-Model ML System (A/B Testing + League Specialization):** A 15-model architecture (5 leagues × 3 algorithms: GradientBoostingRegressor, RandomForestRegressor, XGBoostRegressor) implemented with 100% local scikit-learn and XGBoost. Models continuously learn from 1155+ historical matches, and auto-retraining triggers after 50 new matches. The system automatically selects the best-performing algorithm per league based on R² metrics.
- **Deterministic Predictions:** All algorithms are designed for deterministic outcomes, with intelligent calculations for corners and yellow cards.
- **Enhanced Prediction Algorithms:** Incorporate H2H analysis, motivation, streak analysis, smart weighting for recent matches, attack-based logic, and consider tournament importance (e.g., World Cup 1.30x motivation multiplier). Separate HOME/AWAY statistics are used for improved accuracy.
- **Team Subscriptions System:** Manages user subscriptions and sends timely notifications with bulk-optimized database operations (O(1) queries per match) and an idempotent design to prevent duplicate alerts.
- **Automated Scheduler (`scheduler.py`):** A two-tier notification system for subscriber alerts (110-130 minutes before kickoff) and full predictions to all users (50-70 minutes before kickoff).
- **Prediction Verification & Statistics:** `/verify` command and scheduler update match results, saving predictions to the database. `/stats` provides overall prediction and betting statistics.
- **Algorithmic Versioning:** Predictions are tagged for statistical analysis.
- **Team Status and League Class:** Accounts for team strength based on league class and top clubs, applying coefficients to attack and defense power.

**System Design Choices:**
- **Modular Structure:** Code is organized into `main.py`, `scheduler.py`, and a `modules/` directory.
- **PostgreSQL Database:** Used for persistent storage of predictions, match results, user analytics, team subscriptions, and ML training data.
- **Polling Mode:** The bot operates in polling mode.
- **User Analytics:** Tracks all bot users and activity in PostgreSQL, updating an Excel file (`users_stats.xlsx`) in real-time.
- **Performance Optimization:** Bulk database operations prevent query storms, notably in the subscription system.

## External Dependencies
- **Telegram Bot API:** For bot interaction via `pyTelegramBotAPI`.
- **Football-Data.org:** Primary source for match schedules, statistics, league standings, team form, top scorers, and H2H statistics.
- **PostgreSQL:** Database for storing predictions, match results, user analytics, and ML training data.
- **scikit-learn:** Local ML library for prediction models (e.g., GradientBoostingRegressor, RandomForestRegressor).
- **XGBoost:** Local ML library for prediction models (XGBoostRegressor).
- **openpyxl:** Python library for creating and updating Excel files with user statistics.