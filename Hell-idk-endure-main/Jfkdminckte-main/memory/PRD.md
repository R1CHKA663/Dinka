# EASY MONEY Casino - Product Requirements Document

## Original Problem Statement
Казино-платформа с играми (Mines, Dice, Bubbles, Tower, Crash, X100, Keno) и реферальной системой. Основные проблемы, которые были решены:
1. Реферальная система не работала при регистрации через Telegram
2. RTP статистика не отслеживалась для всех игр
3. Система промо-кодов и балансов требовала доработки

## User Personas
- **Игроки**: Пользователи из СНГ, играющие в казино-игры
- **Рефереры**: Пользователи, привлекающие новых игроков за бонусы
- **Администраторы**: Управление RTP, промо-кодами, пользователями

## Core Requirements
1. ✅ Полная работа реферальной системы (Demo + Telegram auth)
2. ✅ RTP tracking для всех игр (Dice, Mines, Bubbles, Tower, Crash, X100)
3. ✅ Dual-balance система (deposit_balance, promo_balance)
4. ✅ Мобильная адаптация админ-панели
5. ✅ Нагрузочное тестирование (скрипт создан, результаты в /app/LOAD_TEST_REPORT.md)

## Architecture
```
/app/
├── backend/
│   ├── server.py         # FastAPI backend (монолит ~5000 строк)
│   └── .env              # MONGO_URL, SECRET_KEY, ADMIN_PASSWORD
├── frontend/
│   ├── src/App.js        # React frontend (монолит ~4300 строк)
│   └── .env              # REACT_APP_BACKEND_URL
└── test_reports/         # Результаты тестирования
```

## What's Been Implemented

### 2026-02-07
- **Referral System Fix**: Исправлена closure-проблема в React - ref_code теперь читается из localStorage в момент авторизации
- **RTP Tracking Complete**: Добавлен track_rtp_stat для Crash, Mines (cashout), Tower (cashout)
- **Keno Removed**: Убрана игра Keno из списка (не используется на сайте)
- **Load Testing**: Создан скрипт `/app/backend/load_test.py` и проведено тестирование
- **SECURITY: Crash game fix**: Убрана отправка crash_point клиенту (критическая уязвимость)
- **SECURITY: DDoS Protection**: Расширенная защита с детектированием паттернов атак
- **SECURITY: Anti-Cheat**: Система обнаружения ботов и автоматизации
- **PERFORMANCE: MongoDB Indexes**: Добавлены индексы для оптимизации запросов
- **Testing**: 14 backend + 5 frontend тестов прошли успешно

### Previous Session
- Система dual-balance (deposit_balance, promo_balance)
- Миграция данных пользователей
- Мобильная адаптация админ-панели
- Sequential registration_number для пользователей

## Key API Endpoints
- `POST /api/auth/telegram` - Telegram авторизация с ref_code
- `POST /api/auth/demo` - Демо авторизация с ref_code
- `GET /api/ref/stats` - Статистика рефералов
- `GET /api/admin/settings` - Настройки и RTP статистика
- `POST /api/payment/mock/complete/{id}` - Мок платежей (тестирование)

## Database Schema
- **users**: id, telegram_id, balance, deposit_balance, promo_balance, invited_by, ref_link, registration_number
- **rtp_stats**: game, total_bets, total_wins, games_count
- **counters**: _id="registration_number", seq

## Known Issues
- Telegram виджет показывает "Bot domain invalid" на preview домене (нормально для тестов)
- Платежи мокнуты для тестирования

## Backlog
1. **P3**: Рефакторинг монолитных файлов (server.py ~5000 строк, App.js ~4300 строк)
2. **P3**: 2FA аутентификация
3. **P3**: Telegram Bot Token Validation (проверка hash)
4. **P3**: Redis для rate limiting (масштабирование)
5. **P3**: IP Whitelist для админ-панели

## Credentials
- Admin password: `ADMIn1@tim`
- Preview URL: https://referfix.preview.emergentagent.com
