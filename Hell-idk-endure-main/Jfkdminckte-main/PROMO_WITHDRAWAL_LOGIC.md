# 💰 Логика Вывода с Промокодами

## Требования

### Сценарий 1: Промокод → Депозит
1. Пользователь активирует промокод (получает бонус + wager)
2. Делает депозит
3. Играет и выигрывает
4. **Правило вывода**: Макс 300₽ (из промо-бонуса) + весь выигрыш с депозитных средств

### Сценарий 2: Депозит → Промокод
1. Пользователь делает депозит
2. Активирует промокод (получает бонус + wager на промо)
3. Играет и выигрывает
4. **Правило вывода**: 300₽ (из промо-бонуса) + выигрыш с депозита (не считается как с промо)

## Реализация

### Новые поля пользователя:
```python
{
  "promo_balance": 0.0,         # Баланс с промокодов
  "deposit_balance": 0.0,       # Баланс с депозитов
  "promo_winnings": 0.0,        # Выигрыш, полученный играя промо-средствами
  "deposit_winnings": 0.0,      # Выигрыш, полученный играя депозитными средствами
  "promo_withdrawal_limit": 300, # Макс вывод с промо
}
```

### Логика игры:
1. При ставке сначала используется `deposit_balance`, потом `promo_balance`
2. При выигрыше:
   - Если играл с `deposit_balance` → прибавка к `deposit_winnings`
   - Если играл с `promo_balance` → прибавка к `promo_winnings`

### Логика вывода:
```python
# Доступно для вывода:
withdrawable = min(promo_balance, 300) + deposit_balance + deposit_winnings
```

## Код

### Функция расчета доступного вывода:
```python
def get_withdrawable_amount(user: dict) -> dict:
    deposit_bal = user.get("deposit_balance", 0)
    promo_bal = user.get("promo_balance", 0)
    deposit_win = user.get("deposit_winnings", 0)
    promo_win = user.get("promo_winnings", 0)
    limit = user.get("promo_withdrawal_limit", 300)
    
    # Промо баланс ограничен 300₽ для вывода
    withdrawable_promo = min(promo_bal, limit)
    
    # Депозитный баланс + выигрыш с депа - без ограничений
    withdrawable_deposit = deposit_bal + deposit_win
    
    # Выигрыш с промо - только после отыгрыша wager
    # (уже входит в promo_balance при отыгрыше)
    
    total = withdrawable_promo + withdrawable_deposit
    
    return {
        "total": total,
        "from_promo": withdrawable_promo,
        "from_deposit": withdrawable_deposit,
        "promo_balance": promo_bal,
        "locked_promo": max(0, promo_bal - limit)  # Заблокировано
    }
```

### Функция ставки:
```python
async def place_bet(user_id: str, bet_amount: float):
    user = await db.users.find_one({"id": user_id})
    
    # Сначала списываем с депозитного баланса
    from_deposit = min(bet_amount, user.get("deposit_balance", 0))
    from_promo = bet_amount - from_deposit
    
    # Обновляем балансы
    updates = {
        "deposit_balance": -from_deposit,
        "promo_balance": -from_promo
    }
    
    await db.users.update_one({"id": user_id}, {"$inc": updates})
    
    # Возвращаем информацию откуда списали
    return {
        "from_deposit": from_deposit,
        "from_promo": from_promo
    }
```

### Функция выигрыша:
```python
async def add_win(user_id: str, win_amount: float, bet_from: dict):
    # Распределяем выигрыш пропорционально источнику ставки
    bet_total = bet_from["from_deposit"] + bet_from["from_promo"]
    
    if bet_from["from_deposit"] > 0:
        # Выигрыш с депозитных средств
        win_deposit = win_amount * (bet_from["from_deposit"] / bet_total)
        updates = {
            "deposit_balance": win_deposit,
            "deposit_winnings": win_deposit - bet_from["from_deposit"]
        }
    
    if bet_from["from_promo"] > 0:
        # Выигрыш с промо средств
        win_promo = win_amount * (bet_from["from_promo"] / bet_total)
        updates.update({
            "promo_balance": win_promo,
            "promo_winnings": win_promo - bet_from["from_promo"]
        })
    
    await db.users.update_one({"id": user_id}, {"$inc": updates})
```

## Миграция существующих пользователей

```python
# Все существующие balance переносятся в deposit_balance
await db.users.update_many(
    {},
    [{
        "$set": {
            "deposit_balance": "$balance",
            "promo_balance": 0,
            "deposit_winnings": 0,
            "promo_winnings": 0,
            "promo_withdrawal_limit": 300
        }
    }]
)
```

## Тесты

### Тест 1: Промо → Деп
1. Промокод: +1000₽ (promo_balance = 1000)
2. Депозит: +500₽ (deposit_balance = 500)
3. Игра (ставка 100₽ с депа): +200₽ → deposit_winnings = 100
4. Вывод доступен: min(1000, 300) + 500 + 100 = 900₽

### Тест 2: Деп → Промо
1. Депозит: +500₽ (deposit_balance = 500)
2. Промокод: +1000₽ (promo_balance = 1000)
3. Игра (ставка 100₽ с депа): +200₽ → deposit_winnings = 100
4. Вывод доступен: 500 + 100 + min(1000, 300) = 900₽

---

**Статус**: Логика разработана, готова к имплементации
