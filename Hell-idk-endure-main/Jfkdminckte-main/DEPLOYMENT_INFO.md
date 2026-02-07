# 🎰 EASY MONEY - Казино Полностью Запущено! ✅

## 📊 Статус Системы

```
✅ Backend (FastAPI)     - РАБОТАЕТ на http://0.0.0.0:8001
✅ Frontend (React)      - РАБОТАЕТ на http://0.0.0.0:3000
✅ MongoDB              - РАБОТАЕТ
✅ Supervisor           - Все сервисы активны
```

## 🔑 Учетные Данные

### Админ-панель
- **Пароль**: `ADMIn1@tim`
- **Доступ**: POST /api/admin/login

### JWT Secret
- **SECRET_KEY**: Сгенерирован и сохранен в `/app/backend/.env`

## 💳 Платежные Системы

Все 5 платежных провайдеров настроены и работают:

### 1. **NicePay** (Карты/СБП)
- Merchant ID: `69850e325cc2d10f488c21c9`
- Secret: `xPJjx-wcRv2-buuoM-JG79o-WGgti`
- Методы: СБП, Карты, Банки

### 2. **1plat** (aaio.so) - Карты/СБП #2
- Shop ID: `1486`
- Secret: `TIMUr@2010`
- Методы: СБП, Карты

### 3. **CryptoBot** - Telegram Crypto
- Token: `525931:AAlplSqVIuDYNgYsOdIUJH0RfivHO1P5hCQ`
- Методы: USDT, TON, BTC, ETH

### 4. **CryptoCloud** - Крипта
- API Key: `eyJ0eXAi...` (полный ключ в .env)
- Shop ID: `Zlaj8rcvtnrUNCjt`
- Методы: 14 криптовалют

### 5. **Через администратора**
- Telegram: @easymoneysupportvip
- Диапазон: 150₽ - 250,000₽
- Автоматическое открытие Telegram при пополнении

## 🎮 Доступные Игры

1. **Mines** - Классический минёр
2. **Dice** - Игра в кости
3. **Tower** - Башня с уровнями
4. **Crash** - Множитель
5. **Bubbles** - Пузыри
6. **X100** - Множитель x100
7. **Слоты** - Множество слот-игр

## 🔧 Управление Сервисами

### Проверка статуса
```bash
sudo supervisorctl status
```

### Перезапуск Backend
```bash
sudo supervisorctl restart backend
```

### Перезапуск Frontend
```bash
sudo supervisorctl restart frontend
```

### Перезапуск всех сервисов
```bash
sudo supervisorctl restart all
```

### Просмотр логов
```bash
# Backend логи
tail -f /var/log/supervisor/backend.out.log
tail -f /var/log/supervisor/backend.err.log

# Frontend логи
tail -f /var/log/supervisor/frontend.out.log
tail -f /var/log/supervisor/frontend.err.log
```

## 🧪 Тестирование API

### Демо-авторизация
```bash
curl -X POST http://localhost:8001/api/auth/demo \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser"}' | jq .
```

### Админ логин
```bash
curl -X POST http://localhost:8001/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"password":"ADMIn1@tim"}' | jq .
```

### Список платежных провайдеров
```bash
curl http://localhost:8001/api/payment/providers | jq .
```

### Онлайн счётчик
```bash
curl http://localhost:8001/api/online | jq .
```

### Игра Mines
```bash
TOKEN="your_jwt_token"

curl -X POST http://localhost:8001/api/games/mines/play \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bombs_count":3,"bet":100}' | jq .
```

### Игра Dice
```bash
curl -X POST http://localhost:8001/api/games/dice/play \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bet":50,"target":50,"direction":"over"}' | jq .
```

### Игра Tower
```bash
curl -X POST http://localhost:8001/api/games/tower/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bet":100,"difficulty":"easy"}' | jq .
```

## 📁 Структура Проекта

```
/app/
├── backend/
│   ├── server.py           # Главный файл FastAPI
│   ├── requirements.txt    # Python зависимости
│   └── .env               # Переменные окружения (API ключи)
│
├── frontend/
│   ├── src/
│   │   ├── App.js         # Главный React компонент
│   │   ├── App.css        # Стили
│   │   └── components/    # UI компоненты
│   ├── public/
│   │   ├── assets/        # Изображения игр
│   │   └── slots.json     # Данные слотов
│   ├── package.json       # Node.js зависимости
│   └── .env              # Frontend переменные
│
└── DEPLOYMENT_INFO.md     # Этот файл
```

## 🌐 URL-адреса

- **Frontend**: https://referfix.preview.emergentagent.com
- **Backend API**: https://referfix.preview.emergentagent.com/api
- **Local Frontend**: http://localhost:3000
- **Local Backend**: http://localhost:8001

## 📝 Важные Переменные (.env)

### Backend (/app/backend/.env)
```bash
MONGO_URL=mongodb://localhost:27017
DB_NAME=easymoney
SECRET_KEY=<сгенерировано>
ADMIN_PASSWORD=ADMIn1@tim

# Платежные системы
ONEPLATPAY_SHOP_ID=1486
ONEPLATPAY_SECRET=TIMUr@2010
CRYPTOCLOUD_API_KEY=eyJ0eXAi...
CRYPTOCLOUD_SHOP_ID=Zlaj8rcvtnrUNCjt
CRYPTOBOT_TOKEN=525931:AAlpl...
NICEPAY_MERCHANT_ID=69850e325cc2d10f488c21c9
NICEPAY_SECRET=xPJjx-wcRv2...
```

### Frontend (/app/frontend/.env)
```bash
REACT_APP_BACKEND_URL=https://referfix.preview.emergentagent.com
WDS_SOCKET_PORT=443
ENABLE_HEALTH_CHECK=false
```

## 🚀 Особенности

- ✅ Честный RTP с криптографическим RNG
- ✅ Rate limiting и DDoS защита
- ✅ JWT авторизация
- ✅ Демо-режим для тестирования
- ✅ Реферальная система
- ✅ Кешбэк система
- ✅ История игр
- ✅ Админ-панель
- ✅ Множественные платежные методы
- ✅ Автоматические webhook'и

## 📞 Поддержка

- **Telegram канал**: https://t.me/easymoneycaspro
- **Telegram поддержка**: @easymoneysupportvip

## ⚠️ Важно

1. **Webhook'и платежных систем** нужно настроить в личных кабинетах провайдеров
2. **Не коммитьте .env файлы** в публичные репозитории
3. **Регулярно делайте бэкапы MongoDB**
4. **Мониторьте логи** на предмет ошибок

## 🎉 Статус: ПОЛНОСТЬЮ РАБОТОСПОСОБЕН

Все системы запущены и протестированы! 🚀

---

**Дата развертывания**: 06 февраля 2026  
**Версия**: 1.0.0  
**Статус**: Production Ready ✅
