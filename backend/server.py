from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import logging
import hashlib
import hmac
import secrets
import random
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import httpx
import json
from decimal import Decimal, ROUND_DOWN
from collections import defaultdict
import asyncio
import time
import aiomysql

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'easymoney')]

# Security - All secrets must be set in environment variables
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    raise ValueError("ADMIN_PASSWORD environment variable is required")
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')  # Optional for demo mode
ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)

MAX_BET = 1000000

# Rate Limiting Configuration - increased for better UX
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMITS = {
    "default": 500,           # 500 requests per minute
    "auth": 30,               # 30 auth attempts per minute
    "games": 300,             # 300 game plays per minute - allow fast play
    "admin": 100,             # 100 admin requests per minute
    "payment": 30,            # 30 payment requests per minute
}

# Blacklist for blocked IPs (DDoS protection)
blocked_ips: set = set()
suspicious_ips: Dict[str, int] = defaultdict(int)

# In-memory rate limit storage
rate_limit_storage: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

# Secure RNG - use system random for critical operations
import os as _os
secure_random = random.SystemRandom()  # Uses /dev/urandom

def get_secure_random() -> float:
    """Get cryptographically secure random float [0, 1)"""
    return secure_random.random()

def get_secure_randint(a: int, b: int) -> int:
    """Get cryptographically secure random integer [a, b]"""
    return secure_random.randint(a, b)

def get_secure_choice(seq):
    """Get cryptographically secure random choice"""
    return secure_random.choice(seq)

def get_secure_shuffle(seq):
    """Cryptographically secure shuffle (in-place)"""
    secure_random.shuffle(seq)
    return seq

def get_client_ip(request: Request) -> str:
    """Get client IP address, handling proxies"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# DDoS Protection - Track request patterns
request_patterns: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "requests": [],
    "burst_count": 0,
    "last_burst": 0,
    "suspicious_score": 0
})

# Anti-cheat: Track timing patterns for games
game_timing_tracker: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

def check_rate_limit(ip: str, category: str = "default") -> bool:
    """Check if request is within rate limit with advanced DDoS protection"""
    # Check if IP is permanently blocked
    if ip in blocked_ips:
        return False
    
    current_time = time.time()
    limit = RATE_LIMITS.get(category, RATE_LIMITS["default"])
    
    # Clean old entries
    rate_limit_storage[ip][category] = [
        t for t in rate_limit_storage[ip][category] 
        if current_time - t < RATE_LIMIT_WINDOW
    ]
    
    # Advanced pattern detection
    pattern = request_patterns[ip]
    pattern["requests"].append(current_time)
    
    # Keep only last 60 seconds of patterns
    pattern["requests"] = [t for t in pattern["requests"] if current_time - t < 60]
    
    # Detect burst patterns (more than 20 requests in 2 seconds)
    recent_requests = [t for t in pattern["requests"] if current_time - t < 2]
    if len(recent_requests) > 20:
        pattern["burst_count"] += 1
        pattern["last_burst"] = current_time
        pattern["suspicious_score"] += 5
    
    # Detect sustained high-frequency (more than 100 requests in 10 seconds)
    mid_term_requests = [t for t in pattern["requests"] if current_time - t < 10]
    if len(mid_term_requests) > 100:
        pattern["suspicious_score"] += 10
    
    # Auto-block if suspicious score exceeds threshold
    if pattern["suspicious_score"] > 50:
        blocked_ips.add(ip)
        logging.warning(f"🚫 DDoS PROTECTION: IP {ip} auto-blocked (suspicious_score={pattern['suspicious_score']})")
        return False
    
    # Decay suspicious score over time
    if current_time - pattern.get("last_decay", 0) > 30:
        pattern["suspicious_score"] = max(0, pattern["suspicious_score"] - 5)
        pattern["last_decay"] = current_time
    
    # Standard rate limit check
    if len(rate_limit_storage[ip][category]) >= limit:
        suspicious_ips[ip] += 1
        if suspicious_ips[ip] > 10:
            blocked_ips.add(ip)
            logging.warning(f"🚫 IP {ip} blocked for excessive rate limit violations")
        return False
    
    # Add new request
    rate_limit_storage[ip][category].append(current_time)
    return True

def check_anti_cheat(user_id: str, game: str, action: str) -> bool:
    """
    Anti-cheat system to detect suspicious timing patterns
    Returns True if action is allowed, False if suspected cheating
    """
    current_time = time.time()
    tracker = game_timing_tracker[user_id][f"{game}_{action}"]
    
    # Keep last 60 seconds of actions
    tracker[:] = [t for t in tracker if current_time - t < 60]
    tracker.append(current_time)
    
    # Detect inhuman speed (actions faster than 100ms apart)
    if len(tracker) >= 2:
        time_diff = tracker[-1] - tracker[-2]
        if time_diff < 0.1:  # Less than 100ms
            logging.warning(f"⚠️ ANTI-CHEAT: User {user_id} suspicious speed in {game}_{action}: {time_diff:.3f}s")
            return False
    
    # Detect automation patterns (too consistent timing)
    if len(tracker) >= 10:
        diffs = [tracker[i] - tracker[i-1] for i in range(1, len(tracker))]
        avg_diff = sum(diffs) / len(diffs)
        variance = sum((d - avg_diff) ** 2 for d in diffs) / len(diffs)
        
        # Bot-like behavior: very low variance (< 0.01) with high frequency
        if variance < 0.01 and avg_diff < 1.0:
            logging.warning(f"⚠️ ANTI-CHEAT: User {user_id} bot-like pattern in {game}_{action}: variance={variance:.4f}")
            return False
    
    return True

def rate_limit(category: str = "default"):
    """Rate limiting decorator with DDoS protection"""
    async def dependency(request: Request):
        ip = get_client_ip(request)
        if not check_rate_limit(ip, category):
            raise HTTPException(
                status_code=429, 
                detail=f"Слишком много запросов. Попробуйте через минуту."
            )
        return True
    return Depends(dependency)

app = FastAPI(title="EASY MONEY Gaming Platform")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== HELPERS ==================

def round_money(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_DOWN))

def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def generate_api_token():
    return secrets.token_hex(30)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Неверный токен")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Токен истек")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")

async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        return True
    except:
        raise HTTPException(status_code=401, detail="Неверный токен")

async def get_settings():
    settings = await db.settings.find_one({"id": "main"}, {"_id": 0})
    if not settings:
        settings = {
            "id": "main", "raceback_percent": 10, "min_withdraw": 150, "min_deposit": 150,
            "dice_rtp": 97, "mines_rtp": 97, "bubbles_rtp": 97, "tower_rtp": 97, 
            "crash_rtp": 97, "x100_rtp": 97, "keno_rtp": 97,
            "dice_bank": 10000, "mines_bank": 10000, "bubbles_bank": 10000, "tower_bank": 10000,
            # RTP tracking statistics
            "dice_total_bets": 0, "dice_total_wins": 0,
            "mines_total_bets": 0, "mines_total_wins": 0,
            "x100_total_bets": 0, "x100_total_wins": 0,
            "tower_total_bets": 0, "tower_total_wins": 0,
            "crash_total_bets": 0, "crash_total_wins": 0,
            "bubbles_total_bets": 0, "bubbles_total_wins": 0,
            "keno_total_bets": 0, "keno_total_wins": 0,
        }
        await db.settings.insert_one(settings)
    return settings

# Background task to expire old pending payments (15 minutes timeout)
PAYMENT_TIMEOUT_MINUTES = 15

async def expire_old_payments():
    """Mark old pending payments as expired"""
    while True:
        try:
            cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=PAYMENT_TIMEOUT_MINUTES)).isoformat()
            result = await db.payments.update_many(
                {
                    "status": "pending",
                    "created_at": {"$lt": cutoff_time}
                },
                {"$set": {"status": "expired"}}
            )
            if result.modified_count > 0:
                logging.info(f"Expired {result.modified_count} old pending payments")
        except Exception as e:
            logging.error(f"Error expiring payments: {e}")
        await asyncio.sleep(60)  # Check every minute

async def check_user_has_deposit_this_month(user_id: str) -> bool:
    """Check if user has at least one completed deposit in the current month or has manual deposit flag"""
    # First check if user has manual deposit flag (admin deposits skip this check)
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "has_manual_deposit": 1})
    if user and user.get("has_manual_deposit"):
        return True
    
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    deposit = await db.payments.find_one({
        "user_id": user_id,
        "status": "completed",
        "created_at": {"$gte": month_start.isoformat()}
    })
    
    return deposit is not None

async def update_bank(game: str, status: str, amount: float, user: dict):
    if user.get("is_youtuber"):
        return
    if status == "win":
        await db.settings.update_one({"id": "main"}, {"$inc": {f"{game}_bank": -amount}})
    else:
        await db.settings.update_one({"id": "main"}, {"$inc": {f"{game}_bank": amount * 0.75}})

# Cashback level system based on total deposits
# Level 1: 0-4999₽ = 5%
# Level 2: 5000-19999₽ = 10%
# Level 3: 20000-49999₽ = 15%
# Level 4: 50000-99999₽ = 20%
# Level 5: 100000-199999₽ = 25%
# Level 6: 200000₽+ = 30%
CASHBACK_LEVELS = [
    {"min_deposit": 0, "percent": 5, "name": "Бронза"},
    {"min_deposit": 5000, "percent": 10, "name": "Серебро"},
    {"min_deposit": 20000, "percent": 15, "name": "Золото"},
    {"min_deposit": 50000, "percent": 20, "name": "Платина"},
    {"min_deposit": 100000, "percent": 25, "name": "Бриллиант"},
    {"min_deposit": 200000, "percent": 30, "name": "Легенда"},
]

def get_cashback_level(total_deposited: float):
    """Get cashback level based on total deposits"""
    level = CASHBACK_LEVELS[0]
    for l in CASHBACK_LEVELS:
        if total_deposited >= l["min_deposit"]:
            level = l
    return level

async def calculate_raceback(user_id: str, bet: float):
    """
    DEPRECATED: Raceback from bets is disabled.
    Cashback is now only given on deposits (see payment completion handlers).
    This function is kept for backwards compatibility but does nothing.
    """
    pass  # Cashback only from deposits now

async def calculate_deposit_cashback(user_id: str, deposit_amount: float):
    """
    Calculate cashback from deposit.
    
    Rules:
    - Cashback is given on EVERY deposit (% of deposit amount)
    - % depends on user's level (total deposits)
    - Cashback accumulates in 'raceback' field
    - User can claim cashback only when balance is 0
    """
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return 0
    
    # Get user's total deposits for level calculation
    total_deposited = user.get("total_deposited", 0)
    level = get_cashback_level(total_deposited)
    percent = level["percent"] / 100
    
    # Cashback is percentage of THIS deposit amount
    cashback_amount = round_money(deposit_amount * percent)
    
    if cashback_amount > 0:
        await db.users.update_one(
            {"id": user_id}, 
            {"$inc": {"raceback": cashback_amount}}
        )
        logging.info(f"Deposit Cashback: {cashback_amount}₽ for user {user_id} (deposit: {deposit_amount}₽, level: {level['name']} {level['percent']}%)")
    
    return cashback_amount

async def decrease_wager(user_id: str, bet: float):
    """Decrease user's wager by bet amount, but not below 0"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "wager": 1})
    if not user:
        return
    
    current_wager = user.get("wager", 0)
    if current_wager <= 0:
        return  # No wager to decrease
    
    # Calculate new wager (minimum 0)
    decrease_amount = min(bet, current_wager)
    new_wager = max(0, current_wager - bet)
    
    await db.users.update_one({"id": user_id}, {"$set": {"wager": new_wager}})

async def check_and_disable_cashback(user_id: str):
    """
    This function is DISABLED - cashback should only be disabled through claim action.
    Keeping function for backwards compatibility but it does nothing.
    """
    # DISABLED: Do not auto-disable cashback based on balance
    # Cashback will only be disabled after user claims it and loses balance
    # This is handled in the claim endpoint instead
    pass

async def track_rtp_stat(game: str, bet_amount: float, win_amount: float):
    """Track RTP statistics for long-term monitoring"""
    await db.settings.update_one(
        {"id": "main"},
        {
            "$inc": {
                f"{game}_total_bets": bet_amount,
                f"{game}_total_wins": win_amount
            }
        }
    )

# ================== PROMO BALANCE SYSTEM ==================

async def get_user_balances(user_id: str) -> dict:
    """Get user's separated balances (deposit vs promo)"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return {"deposit_balance": 0, "promo_balance": 0, "total": 0}
    
    # For backward compatibility: old users have all in 'balance'
    # New users have 'deposit_balance' and 'promo_balance'
    if "deposit_balance" not in user:
        # Migrate old balance to deposit_balance
        total_balance = user.get("balance", 0)
        return {
            "deposit_balance": total_balance,
            "promo_balance": 0,
            "total": total_balance
        }
    
    deposit_bal = user.get("deposit_balance", 0)
    promo_bal = user.get("promo_balance", 0)
    return {
        "deposit_balance": deposit_bal,
        "promo_balance": promo_bal,
        "total": deposit_bal + promo_bal
    }

async def deduct_bet(user_id: str, bet_amount: float) -> dict:
    """Deduct bet from user balances (deposit first, then promo)"""
    balances = await get_user_balances(user_id)
    
    # Deduct from deposit first
    from_deposit = min(bet_amount, balances["deposit_balance"])
    from_promo = bet_amount - from_deposit
    
    # Update database
    if from_deposit > 0 and from_promo > 0:
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"deposit_balance": -from_deposit, "promo_balance": -from_promo}}
        )
    elif from_deposit > 0:
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"deposit_balance": -from_deposit}}
        )
    elif from_promo > 0:
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"promo_balance": -from_promo}}
        )
    
    return {"from_deposit": from_deposit, "from_promo": from_promo}

async def add_win(user_id: str, win_amount: float, bet_source: dict):
    """Add winnings to appropriate balance based on bet source"""
    from_deposit = bet_source["from_deposit"]
    from_promo = bet_source["from_promo"]
    total_bet = from_deposit + from_promo
    
    if total_bet == 0:
        return
    
    # Distribute winnings proportionally
    if from_deposit > 0:
        win_to_deposit = win_amount * (from_deposit / total_bet)
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"deposit_balance": win_to_deposit}}
        )
    
    if from_promo > 0:
        win_to_promo = win_amount * (from_promo / total_bet)
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"promo_balance": win_to_promo}}
        )

async def get_withdrawable_amount(user_id: str) -> dict:
    """
    Calculate withdrawable amount with promo limit (300₽).
    
    Rules:
    - Deposit balance is ALWAYS withdrawable (no wager requirement)
    - Promo balance limited to max 300₽ withdrawal
    - Promo balance requires wager to be played through first
    - Wager ONLY blocks promo_balance, never deposit_balance
    """
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return {"total": 0, "from_deposit": 0, "from_promo": 0, "locked_promo": 0, "wager": 0}
    
    # Get balances
    deposit_bal = user.get("deposit_balance", user.get("balance", 0))  # Backward compat
    promo_bal = user.get("promo_balance", 0)
    promo_limit = user.get("promo_withdrawal_limit", 300)
    user_wager = user.get("wager", 0)
    
    # Deposit balance - ALWAYS withdrawable, no wager needed
    withdrawable_deposit = deposit_bal
    
    # Promo balance - limited to 300₽ AND requires wager to be 0
    if user_wager > 0:
        # Wager is active - promo balance is LOCKED until wager is played through
        withdrawable_promo = 0
        locked_promo = promo_bal
    else:
        # Wager is complete - promo balance available up to 300₽ limit
        withdrawable_promo = min(promo_bal, promo_limit)
        locked_promo = max(0, promo_bal - promo_limit)
    
    total = withdrawable_deposit + withdrawable_promo
    
    return {
        "total": total,
        "from_deposit": withdrawable_deposit,
        "from_promo": withdrawable_promo,
        "locked_promo": locked_promo,
        "promo_balance_full": promo_bal,
        "wager": user_wager
    }

# Referral level system
# Level 1: 0-9 deposited refs = 10%
# Level 2: 10-24 deposited refs = 20%
# Level 3: 25-49 deposited refs = 30%
# Level 4: 50+ deposited refs = 40%
REF_LEVELS = [
    {"min_refs": 0, "percent": 10, "name": "Новичок"},
    {"min_refs": 10, "percent": 20, "name": "Партнёр"},
    {"min_refs": 25, "percent": 30, "name": "Мастер"},
    {"min_refs": 50, "percent": 40, "name": "Легенда"},
]

def get_ref_level(deposited_refs: int):
    """Get referral level based on number of refs who deposited"""
    level = REF_LEVELS[0]
    for l in REF_LEVELS:
        if deposited_refs >= l["min_refs"]:
            level = l
    return level

async def add_ref_bonus(user_id: str, deposit_amount: float):
    """Add referral bonus when user deposits"""
    logging.info(f"💰 ADD_REF_BONUS START: user_id={user_id}, amount={deposit_amount}")
    
    # Reload user to get fresh data
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        logging.warning(f"❌ add_ref_bonus: User {user_id} not found")
        return
        
    if not user.get("invited_by"):
        logging.info(f"ℹ️ add_ref_bonus: User {user_id} has no inviter")
        return
    
    inviter_ref_link = user.get("invited_by")
    logging.info(f"🔍 add_ref_bonus: User {user_id} invited by ref_link={inviter_ref_link}")
    
    # Get inviter by ref_link
    inviter = await db.users.find_one({"ref_link": inviter_ref_link}, {"_id": 0})
    if not inviter:
        logging.warning(f"❌ add_ref_bonus: Inviter with ref_link={inviter_ref_link} not found")
        return
    
    # Count total deposits before this one (excluding current deposit)
    total_before = user.get("total_deposited", 0) - deposit_amount
    is_first_deposit = total_before <= 0.01  # First deposit (with small margin for float issues)
    
    logging.info(f"📊 add_ref_bonus: total_before={total_before}, is_first={is_first_deposit}")
    
    # If this is user's first deposit, increment deposited_refs for inviter
    if is_first_deposit:
        result = await db.users.update_one({"id": inviter["id"]}, {"$inc": {"deposited_refs": 1}})
        logging.info(f"✅ add_ref_bonus: FIRST DEPOSIT! deposited_refs +1 (modified={result.modified_count})")
        # Refresh inviter data to get updated deposited_refs
        inviter = await db.users.find_one({"id": inviter["id"]}, {"_id": 0})
        logging.info(f"📊 Inviter {inviter['id']} now has {inviter.get('deposited_refs', 0)} deposited refs")
    
    # Get inviter's deposited refs count
    deposited_refs = inviter.get("deposited_refs", 0)
    
    # Get level and percent based on deposited refs
    level = get_ref_level(deposited_refs)
    percent = level["percent"] / 100
    
    bonus = round_money(deposit_amount * percent)
    # Add bonus to income AND deposit_balance so user can use it
    result = await db.users.update_one(
        {"id": inviter["id"]}, 
        {"$inc": {
            "income": bonus, 
            "income_all": bonus,
            "deposit_balance": bonus,  # Add to deposit_balance so user can withdraw/use it
            "balance": bonus  # Also update old balance field for compatibility
        }}
    )
    logging.info(f"💵 REF BONUS: {bonus}₽ ({level['percent']}% level={level['name']}) added to inviter {inviter['id']} (modified={result.modified_count})")

def should_player_win(rtp: float, user: dict, multiplier: float = 2.0, game: str = "default") -> bool:
    """
    RTP (Return To Player) - процент возврата игроку на дистанции.
    Например: 95% RTP = на каждые 100₽ ставок, игрок в среднем получит 95₽ обратно.
    
    Формула: win_chance = (RTP / 100) / multiplier
    Примеры:
    - RTP 95%, множитель 2x: шанс выигрыша = 95/100/2 = 47.5%
    - RTP 95%, множитель 10x: шанс выигрыша = 95/100/10 = 9.5%
    - RTP 90%, множитель 2x: шанс выигрыша = 90/100/2 = 45%
    """
    # YouTube режим - всегда больше шансов
    if user.get("is_youtuber"):
        return get_secure_random() < 0.75
    
    # Дрейн система - контроль больших выигрышей
    if user.get("is_drain"):
        drain_chance = user.get("is_drain_chance", 20)
        if get_secure_randint(1, 100) <= drain_chance:
            return False
    
    # Рассчитываем шанс выигрыша на основе RTP и множителя
    # RTP напрямую влияет на шансы: чем выше RTP, тем выше шанс
    win_chance = (rtp / 100) / multiplier
    
    # Проверяем выигрыш с криптографически безопасным random
    return get_secure_random() < win_chance

def should_player_win_step(rtp: float, user: dict, multiplier: float, step: int = 1, game: str = "default") -> bool:
    """
    RTP для многоступенчатых игр (Mines, Tower).
    Использует корень N-й степени чтобы общий RTP был корректным на дистанции.
    
    Формула: step_chance = ((RTP / 100) / multiplier) ^ (1 / step)
    
    Это гарантирует что после N шагов общий шанс = RTP / multiplier
    """
    # YouTube режим - всегда больше шансов
    if user.get("is_youtuber"):
        return get_secure_random() < 0.95
    
    # Дрейн система
    if user.get("is_drain"):
        drain_chance = user.get("is_drain_chance", 20)
        if get_secure_randint(1, 100) <= drain_chance:
            return False
    
    # Базовый шанс для всей игры
    base_chance = (rtp / 100) / multiplier
    
    # Корень N-й степени для текущего шага
    # Это означает: если игрок пройдёт все step шагов, общий шанс будет base_chance
    if step > 1:
        step_chance = base_chance ** (1 / step)
    else:
        step_chance = base_chance
    
    # Минимум 10% шанс на каждый шаг чтобы игра была интересной
    step_chance = max(0.10, min(0.95, step_chance))
    
    return get_secure_random() < step_chance

# ================== STARTUP ==================

@app.on_event("startup")
async def startup():
    await get_settings()
    
    # Create MongoDB indexes for performance optimization
    try:
        # Users collection indexes
        await db.users.create_index("id", unique=True)
        await db.users.create_index("telegram_id", sparse=True)
        await db.users.create_index("ref_link", sparse=True)
        await db.users.create_index("invited_by", sparse=True)
        await db.users.create_index("registration_number")
        await db.users.create_index("created_at")
        
        # Bets collection indexes (for history)
        await db.bets.create_index([("created_at", -1)])
        await db.bets.create_index("user_id")
        await db.bets.create_index([("user_id", 1), ("created_at", -1)])
        
        # Payments collection indexes
        await db.payments.create_index("user_id")
        await db.payments.create_index("status")
        await db.payments.create_index([("created_at", -1)])
        
        # Crash bets indexes
        await db.crash_bets.create_index("user_id")
        await db.crash_bets.create_index([("created_at", -1)])
        
        # RTP stats index
        await db.rtp_stats.create_index("game", unique=True)
        
        logging.info("✅ MongoDB indexes created successfully")
    except Exception as e:
        logging.warning(f"Index creation warning: {e}")
    
    # Migration: Add missing fields to existing users
    try:
        # Update users without deposited_refs
        result = await db.users.update_many(
            {"deposited_refs": {"$exists": False}},
            {"$set": {"deposited_refs": 0}}
        )
        if result.modified_count > 0:
            logging.info(f"Migration: Added deposited_refs to {result.modified_count} users")
        
        # Update users without total_deposited
        result = await db.users.update_many(
            {"total_deposited": {"$exists": False}},
            {"$set": {"total_deposited": 0.0}}
        )
        if result.modified_count > 0:
            logging.info(f"Migration: Added total_deposited to {result.modified_count} users")
            
        # Calculate total_deposited from completed payments for users who have deposits
        async for user in db.users.find({"deposit": {"$gt": 0}}, {"_id": 0, "id": 1}):
            total = 0.0
            async for payment in db.payments.find({"user_id": user["id"], "status": "completed"}, {"_id": 0, "amount": 1}):
                total += payment.get("amount", 0)
            
            if total > 0:
                await db.users.update_one(
                    {"id": user["id"]},
                    {"$set": {"total_deposited": total}}
                )
                logging.info(f"Migration: Set total_deposited={total} for user {user['id']}")
    except Exception as e:
        logging.error(f"Migration error: {e}")
    
    # Start background task to expire old payments
    asyncio.create_task(expire_old_payments())
    logger.info("EASY MONEY Gaming Platform started")

@app.on_event("shutdown")
async def shutdown():
    client.close()

# ================== AUTH ==================

@api_router.post("/auth/telegram")
async def telegram_auth(request: Request):
    data = await request.json()
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    
    # LOG: Received data
    ref_code = data.get("ref_code")
    logging.info(f"🔍 TELEGRAM AUTH: tg_id={data.get('id')}, ref_code={ref_code}")
    
    user = await db.users.find_one({"telegram_id": data.get("id")}, {"_id": 0})
    
    if user:
        logging.info(f"✅ EXISTING USER: {user['id']}, invited_by={user.get('invited_by')}")
        await db.users.update_one({"telegram_id": data.get("id")}, {"$set": {
            "name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            "username": data.get("username", ""),
            "img": data.get("photo_url", "/logo.png"),
            "last_login": datetime.now(timezone.utc).isoformat(),
            "last_ip": client_ip
        }})
        user = await db.users.find_one({"telegram_id": data.get("id")}, {"_id": 0})
    else:
        user_id = str(uuid.uuid4())
        ref_link = secrets.token_hex(5)
        invited_by = None
        
        # Get registration number using atomic counter (optimized for scale)
        counter_result = await db.counters.find_one_and_update(
            {"_id": "registration_number"},
            {"$inc": {"seq": 1}},
            return_document=True,
            upsert=True
        )
        registration_number = counter_result["seq"]
        
        if ref_code:
            logging.info(f"🔍 SEARCHING INVITER: ref_code={ref_code}")
            inviter = await db.users.find_one({"ref_link": ref_code}, {"_id": 0})
            if inviter:
                invited_by = ref_code  # Store ref_link, not ID
                logging.info(f"✅ INVITER FOUND: {inviter['id']}, name={inviter.get('name')}")
                result = await db.users.update_one({"id": inviter["id"]}, {"$inc": {"referalov": 1}})
                logging.info(f"✅ REFERALOV UPDATED: modified_count={result.modified_count}")
            else:
                logging.warning(f"❌ INVITER NOT FOUND: ref_code={ref_code}")
        else:
            logging.info(f"ℹ️ NO REF_CODE provided")
        
        user = {
            "id": user_id, "telegram_id": data.get("id"), 
            "username": data.get("username", ""),
            "name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            "img": data.get("photo_url", "/logo.png"),
            "balance": 0.0, "deposit": 0.0, "raceback": 0.0, "referalov": 0,
            "deposit_balance": 0.0, "promo_balance": 0.0, "promo_withdrawal_limit": 300.0,
            "deposited_refs": 0, "total_deposited": 0.0,
            "income": 0.0, "income_all": 0.0, "ref_link": ref_link, "invited_by": invited_by,
            "is_admin": False, "is_ban": False, "is_ban_comment": None,
            "is_youtuber": False, "is_drain": False, "is_drain_chance": 20.0, "wager": 0.0,
            "registration_number": registration_number,  # NEW: Sequential number
            "api_token": generate_api_token(), "game_token": generate_api_token(),
            "register_ip": client_ip, "last_ip": client_ip,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user)
        logging.info(f"✅ NEW USER CREATED: #{registration_number}, id={user_id}, invited_by={invited_by}")
        user = await db.users.find_one({"telegram_id": data.get("id")}, {"_id": 0})
    
    return {"success": True, "token": create_token(user["id"]), "user": user}

@api_router.post("/auth/demo")
async def demo_auth(request: Request, _=rate_limit("auth")):
    client_ip = get_client_ip(request)
    
    # Get parameters from request body
    try:
        data = await request.json()
        username = data.get("username", "demo_user")
        ref_code = data.get("ref_code")
    except:
        username = "demo_user"
        ref_code = None
    
    user = await db.users.find_one({"username": username}, {"_id": 0})
    
    if not user:
        user_id = str(uuid.uuid4())
        ref_link = secrets.token_hex(5)
        
        # Get registration number using atomic counter (optimized for scale)
        counter_result = await db.counters.find_one_and_update(
            {"_id": "registration_number"},
            {"$inc": {"seq": 1}},
            return_document=True,
            upsert=True
        )
        registration_number = counter_result["seq"]
        
        # Process referral code for demo users too
        invited_by = None
        if ref_code:
            logging.info(f"🔍 DEMO AUTH: Searching for inviter with ref_link={ref_code}")
            inviter = await db.users.find_one({"ref_link": ref_code}, {"_id": 0})
            if inviter:
                invited_by = ref_code  # Store ref_link, not ID
                logging.info(f"✅ DEMO AUTH: Found inviter {inviter['id']}, setting invited_by={ref_code}")
                await db.users.update_one({"id": inviter["id"]}, {"$inc": {"referalov": 1}})
            else:
                logging.warning(f"❌ DEMO AUTH: No inviter found with ref_link={ref_code}")
        else:
            logging.info("ℹ️ DEMO AUTH: No ref_code provided")
        
        user = {
            "id": user_id, "telegram_id": random.randint(100000000, 999999999),
            "username": username, "name": username, "img": "/logo.png",
            "balance": 1000.0, "deposit": 0.0, "raceback": 0.0, "referalov": 0,
            "deposit_balance": 1000.0, "promo_balance": 0.0, "promo_withdrawal_limit": 300.0,
            "deposited_refs": 0, "total_deposited": 0.0,
            "income": 0.0, "income_all": 0.0, "ref_link": ref_link, "invited_by": invited_by,
            "is_admin": False, "is_ban": False, "is_ban_comment": None,
            "is_youtuber": False, "is_drain": False, "is_drain_chance": 20.0, "wager": 0.0,
            "is_demo": True,
            "registration_number": registration_number,  # NEW
            "api_token": generate_api_token(), "game_token": generate_api_token(),
            "register_ip": client_ip, "last_ip": client_ip,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user)
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
    
    return {"success": True, "token": create_token(user["id"]), "user": user}

@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"success": True, "user": user}

# ================== GAMES - MINES ==================

def get_mines_coefficient(bombs: int, opened: int) -> float:
    coeff = 1.0
    for i in range(opened):
        coeff *= (25 - i) / (25 - bombs - i)
    return round(coeff, 2)

@api_router.post("/games/mines/play")
async def mines_play(request: Request, user: dict = Depends(get_current_user), _=rate_limit("games")):
    data = await request.json()
    if user.get("is_ban"):
        raise HTTPException(status_code=403, detail="Ваш аккаунт заблокирован")
    
    active_game = await db.mines_games.find_one({"user_id": user["id"], "active": True}, {"_id": 0})
    if active_game:
        raise HTTPException(status_code=400, detail="У вас есть активная игра")
    
    bet = min(float(data.get("bet", 10)), user["balance"], MAX_BET)
    bombs = int(data.get("bombs", 5))
    if bet < 1:
        raise HTTPException(status_code=400, detail="Недостаточно средств")
    
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": -bet}})
    await decrease_wager(user["id"], bet)
    
    all_positions = list(range(1, 26))
    random.shuffle(all_positions)
    mines_positions = all_positions[:bombs]
    
    game = {
        "id": str(uuid.uuid4()), "user_id": user["id"], "bet": bet, "bombs": bombs,
        "mines": mines_positions, "clicked": [], "win": 0.0, "active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.mines_games.insert_one(game)
    
    return {"success": True, "balance": round_money(user["balance"] - bet), "game_id": game["id"]}

@api_router.post("/games/mines/press")
async def mines_press(request: Request, user: dict = Depends(get_current_user), _=rate_limit("games")):
    data = await request.json()
    cell = int(data.get("cell", 1))
    
    game = await db.mines_games.find_one({"user_id": user["id"], "active": True}, {"_id": 0})
    if not game:
        raise HTTPException(status_code=400, detail="У вас нет активных игр")
    
    if cell in game["clicked"]:
        raise HTTPException(status_code=400, detail="Вы уже нажали на эту ячейку")
    
    settings = await get_settings()
    rtp = settings.get("mines_rtp", 97)
    clicked = game["clicked"] + [cell]
    current_step = len(clicked)
    
    current_coeff = get_mines_coefficient(game["bombs"], current_step)
    potential_win = round_money(game["bet"] * current_coeff)
    
    # RTP determines if player wins this click
    # Use step-based formula for fair multi-step RTP
    bank = settings.get("mines_bank", 10000)
    
    if user.get("is_youtuber"):
        hit_mine = False  # YouTubers always safe
    elif potential_win > bank:
        hit_mine = True  # Bank protection
    else:
        # Use step-based RTP for correct long-term returns
        hit_mine = not should_player_win_step(rtp, user, current_coeff, current_step, "mines")
    
    # Adjust mines positions based on result
    if hit_mine:
        # Make sure the clicked cell has a mine
        if cell not in game["mines"]:
            other_clicked = [c for c in clicked if c != cell]
            available = [i for i in range(1, 26) if i not in other_clicked]
            random.shuffle(available)
            new_mines = [cell] + [p for p in available if p != cell][:game["bombs"]-1]
            game["mines"] = new_mines
            await db.mines_games.update_one({"id": game["id"]}, {"$set": {"mines": new_mines}})
    else:
        # Make sure the clicked cell is safe
        if cell in game["mines"]:
            # Move the mine to another position
            available = [i for i in range(1, 26) if i not in clicked and i not in game["mines"]]
            if available:
                new_mine_pos = random.choice(available)
                new_mines = [m if m != cell else new_mine_pos for m in game["mines"]]
                game["mines"] = new_mines
                await db.mines_games.update_one({"id": game["id"]}, {"$set": {"mines": new_mines}})
    
    if hit_mine:
        await db.mines_games.update_one({"id": game["id"]}, {"$set": {"active": False, "clicked": clicked, "win": 0}})
        await update_bank("mines", "lose", game["bet"], user)
        await calculate_raceback(user["id"], game["bet"])
        
        # Track RTP statistics for Mines (loss)
        await track_rtp_stat("mines", game["bet"], 0)
        
        # Check if cashback should be disabled (user claimed and lost)
        await check_and_disable_cashback(user["id"])
        
        return {"success": True, "status": "lose", "cell": cell, "mines": game["mines"]}
    else:
        coeff = get_mines_coefficient(game["bombs"], len(clicked))
        win = round_money(game["bet"] * coeff)
        await db.mines_games.update_one({"id": game["id"]}, {"$set": {"clicked": clicked, "win": win}})
        
        if len(clicked) == 25 - game["bombs"]:
            await db.mines_games.update_one({"id": game["id"]}, {"$set": {"active": False}})
            await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": win}})
            await update_bank("mines", "win", win - game["bet"], user)
            user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
            return {"success": True, "status": "finish", "win": win, "coefficient": coeff, "balance": user_data["balance"], "mines": game["mines"]}
        
        return {"success": True, "status": "continue", "win": win, "coefficient": coeff, "clicked": clicked}

@api_router.post("/games/mines/take")
async def mines_take(user: dict = Depends(get_current_user)):
    game = await db.mines_games.find_one({"user_id": user["id"], "active": True}, {"_id": 0})
    if not game:
        raise HTTPException(status_code=400, detail="У вас нет активных игр")
    if not game["clicked"]:
        raise HTTPException(status_code=400, detail="Сделайте хотя бы один клик")
    
    win = game["win"]
    if win <= 0:
        raise HTTPException(status_code=400, detail="Нечего забирать")
    
    await db.mines_games.update_one({"id": game["id"]}, {"$set": {"active": False}})
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": win}})
    await update_bank("mines", "win", win - game["bet"], user)
    await track_rtp_stat("mines", game["bet"], win)
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"success": True, "win": win, "balance": user_data["balance"], "mines": game["mines"]}

@api_router.get("/games/mines/current")
async def mines_current(user: dict = Depends(get_current_user)):
    game = await db.mines_games.find_one({"user_id": user["id"], "active": True}, {"_id": 0})
    if game:
        return {"success": True, "active": True, "win": game["win"], "clicked": game["clicked"], "bet": game["bet"], "bombs": game["bombs"]}
    return {"success": True, "active": False}

# ================== GAMES - DICE ==================

@api_router.post("/games/dice/play")
async def dice_play(request: Request, user: dict = Depends(get_current_user), _=rate_limit("games")):
    data = await request.json()
    if user.get("is_ban"):
        raise HTTPException(status_code=403, detail="Ваш аккаунт заблокирован")
    
    # Anti-cheat check
    if not check_anti_cheat(user["id"], "dice", "play"):
        raise HTTPException(status_code=429, detail="Слишком быстрые действия. Подождите немного.")
    
    bet = min(float(data.get("bet", 10)), user["balance"], MAX_BET)
    chance = float(data.get("chance", 50))
    game_type = data.get("type", data.get("direction", "under"))  # 'under' or 'over'
    
    if bet < 1:
        raise HTTPException(status_code=400, detail="Недостаточно средств")
    
    settings = await get_settings()
    rtp = settings.get("dice_rtp", 97)
    
    # Calculate multiplier: 99 / chance (house edge ~1%)
    multiplier = round(99 / chance, 2)
    potential_win = round_money(bet * multiplier)
    
    # RTP determines if player wins
    # Formula: win_chance = (RTP/100) / multiplier
    # This gives correct RTP on long distance
    bank = settings.get("dice_bank", 10000)
    
    if user.get("is_youtuber"):
        is_win = get_secure_random() < 0.75
    elif potential_win - bet > bank:
        is_win = False  # Bank protection
    else:
        is_win = should_player_win(rtp, user, multiplier, "dice")
    
    # Generate roll based on result
    if is_win:
        if game_type == "under":
            roll = random.randint(0, int(chance) - 1)
        else:
            roll = random.randint(int(chance) + 1, 99)
    else:
        if game_type == "under":
            roll = random.randint(int(chance), 99)
        else:
            roll = random.randint(0, int(chance))
    
    if is_win:
        win = potential_win
        balance_change = win - bet
        await update_bank("dice", "win", win - bet, user)
    else:
        win = 0
        balance_change = -bet
        await update_bank("dice", "lose", bet, user)
        await calculate_raceback(user["id"], bet)
    
    # Update balance
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": balance_change}})
    # Decrease wager properly (not below 0)
    await decrease_wager(user["id"], bet)
    
    # Track RTP statistics for Dice
    await track_rtp_stat("dice", bet, win if win > 0 else 0)
    
    # Check if cashback should be disabled (after loss)
    if not is_win:
        await check_and_disable_cashback(user["id"])
    
    # Save game to history
    await db.dice_games.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "bet": bet,
        "chance": chance,
        "type": game_type,
        "roll": roll,
        "win": win,
        "multiplier": multiplier if is_win else 0,
        "status": "win" if is_win else "lose",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {
        "success": True, 
        "roll": roll,
        "win": win, 
        "balance": user_data["balance"], 
        "multiplier": multiplier,
        "type": game_type,
        "chance": chance
    }

# ================== GAMES - BUBBLES ==================

@api_router.post("/games/bubbles/play")
async def bubbles_play(request: Request, user: dict = Depends(get_current_user), _=rate_limit("games")):
    data = await request.json()
    if user.get("is_ban"):
        raise HTTPException(status_code=403, detail="Ваш аккаунт заблокирован")
    
    # Anti-cheat check
    if not check_anti_cheat(user["id"], "bubbles", "play"):
        raise HTTPException(status_code=429, detail="Слишком быстрые действия. Подождите немного.")
    
    bet = min(float(data.get("bet", 10)), user["balance"], MAX_BET)
    target = float(data.get("target", 2))
    
    if bet < 1:
        raise HTTPException(status_code=400, detail="Недостаточно средств")
    if target < 1.05 or target > 100:
        raise HTTPException(status_code=400, detail="Цель должна быть от 1.05 до 100")
    
    settings = await get_settings()
    rtp = settings.get("bubbles_rtp", 97)
    
    # RTP-based result generation - lower multipliers are more common
    # Use exponential distribution for realistic bubble popping
    base_mult = 1.0
    
    # Check if player should win based on RTP
    # Target multiplier is what player aims for
    if user.get("is_youtuber") or should_player_win(rtp, user, target, "bubbles"):
        # Player wins - bubble grows past target
        max_mult = target + random.uniform(0.1, min(5, target * 0.5))
    else:
        # Player loses - bubble pops before target
        # More realistic distribution - lower values more likely
        r = random.random()
        if r < 0.5:
            max_mult = random.uniform(1.0, 1.5)  # 50% chance: 1.0-1.5x
        elif r < 0.8:
            max_mult = random.uniform(1.5, target * 0.5)  # 30% chance: 1.5-half of target
        else:
            max_mult = random.uniform(target * 0.5, target - 0.01)  # 20% chance: close to target
    
    is_win = max_mult >= target
    result_mult = round(max_mult, 2)
    
    if is_win:
        win = round_money(bet * target)
        balance_change = win - bet
        await update_bank("bubbles", "win", win - bet, user)
    else:
        win = 0
        balance_change = -bet
        await update_bank("bubbles", "lose", bet, user)
        await calculate_raceback(user["id"], bet)
    
    # Update balance
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": balance_change}})
    # Decrease wager properly (not below 0)
    await decrease_wager(user["id"], bet)
    
    # Track RTP statistics for Bubbles (track net result, not gross win)
    await track_rtp_stat("bubbles", bet, win)
    
    # Check if cashback should be disabled (after loss)
    if not is_win:
        await check_and_disable_cashback(user["id"])
    
    # Save game to history
    await db.bubbles_games.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "bet": bet,
        "target": target,
        "result": result_mult,
        "win": win,
        "coef": target if is_win else result_mult,
        "status": "win" if is_win else "lose",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    return {"success": True, "status": "win" if is_win else "lose", "result": result_mult, "win": win, "balance": user_data["balance"]}

# ================== PLINKO GAME ==================

# Tower game multipliers by difficulty and row
# LOW = easy to pass, small multipliers (1 bomb per row)
# HIGH = hard to pass, big multipliers (3 bombs per row)
TOWER_MULTIPLIERS = {
    # LOW difficulty: 1 bomb, 3 safe - EASY to pass, SMALL multipliers
    "low": {
        1: 1.12, 2: 1.25, 3: 1.40, 4: 1.56, 5: 1.75,
        6: 1.96, 7: 2.19, 8: 2.45, 9: 2.75
    },
    # MEDIUM difficulty: 2 bombs, 2 safe - balanced
    "medium": {
        1: 1.47, 2: 2.18, 3: 3.27, 4: 4.89, 5: 7.34,
        6: 11.0, 7: 16.51, 8: 24.77, 9: 37.15
    },
    # HIGH difficulty: 3 bombs, 1 safe - HARD to pass, BIG multipliers  
    "high": {
        1: 1.96, 2: 3.92, 3: 7.84, 4: 15.68, 5: 31.36,
        6: 62.72, 7: 125.44, 8: 250.88, 9: 501.77
    }
}

def get_tower_bombs_count(difficulty: str) -> int:
    """Get number of bombs per row based on difficulty"""
    if difficulty == "low":
        return 1  # 3 safe out of 4 - EASY
    elif difficulty == "medium":
        return 2  # 2 safe out of 4
    else:  # high
        return 3  # 1 safe out of 4 - HARD

@api_router.post("/games/tower/start")
async def tower_start(request: Request, user: dict = Depends(get_current_user), _=rate_limit("games")):
    """Start Tower game"""
    data = await request.json()
    if user.get("is_ban"):
        raise HTTPException(status_code=403, detail="Ваш аккаунт заблокирован")
    
    # Check for active game
    active_game = await db.tower_games.find_one({"user_id": user["id"], "active": True})
    if active_game:
        raise HTTPException(status_code=400, detail="У вас есть активная игра")
    
    bet = min(float(data.get("bet", 10)), user["balance"], MAX_BET)
    difficulty = data.get("difficulty", "medium").lower()
    
    if difficulty not in ["low", "medium", "high"]:
        difficulty = "medium"
    
    if bet < 1:
        raise HTTPException(status_code=400, detail="Недостаточно средств")
    
    # Deduct bet
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": -bet}})
    # Decrease wager properly (not below 0)
    await decrease_wager(user["id"], bet)
    
    # Generate bomb positions for all 9 rows using secure random
    bombs_per_row = get_tower_bombs_count(difficulty)
    bombs_map = {}
    
    for row in range(1, 10):  # Rows 1-9
        positions = [1, 2, 3, 4]
        get_secure_shuffle(positions)  # Cryptographically secure shuffle
        bombs_map[str(row)] = positions[:bombs_per_row]
    
    game = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "bet": bet,
        "difficulty": difficulty,
        "bombs": bombs_map,
        "current_row": 0,
        "path": [],  # Player's chosen path
        "win": 0.0,
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.tower_games.insert_one(game)
    
    return {
        "success": True,
        "balance": round_money(user["balance"] - bet),
        "game_id": game["id"],
        "difficulty": difficulty,
        "bombs_per_row": bombs_per_row
    }

@api_router.post("/games/tower/step")
async def tower_step(request: Request, user: dict = Depends(get_current_user), _=rate_limit("games")):
    """Make a step in Tower game"""
    data = await request.json()
    column = int(data.get("column", 1))  # 1-4
    
    if column < 1 or column > 4:
        raise HTTPException(status_code=400, detail="Неверная позиция")
    
    game = await db.tower_games.find_one({"user_id": user["id"], "active": True}, {"_id": 0})
    if not game:
        raise HTTPException(status_code=400, detail="У вас нет активной игры")
    
    next_row = game["current_row"] + 1
    if next_row > 9:
        raise HTTPException(status_code=400, detail="Вы уже достигли вершины")
    
    settings = await get_settings()
    rtp = settings.get("tower_rtp", 97)
    bank = settings.get("tower_bank", 10000)
    
    # Get multiplier for this step
    multiplier = TOWER_MULTIPLIERS[game["difficulty"]][next_row]
    potential_win = round_money(game["bet"] * multiplier)
    
    bombs_in_row = game["bombs"][str(next_row)]
    
    # RTP determines if player wins this step
    # Use step-based formula for fair multi-step RTP
    if user.get("is_youtuber"):
        hit_bomb = False  # YouTubers always safe
    elif potential_win > bank:
        hit_bomb = True  # Bank protection
    else:
        # Use step-based RTP for correct long-term returns
        hit_bomb = not should_player_win_step(rtp, user, multiplier, next_row, "tower")
    
    # Adjust bomb positions based on result
    if hit_bomb:
        # Make sure player's column has a bomb
        if column not in bombs_in_row:
            safe_positions = [p for p in [1, 2, 3, 4] if p not in bombs_in_row]
            if column in safe_positions:
                new_bombs = [column] + bombs_in_row[:-1] if len(bombs_in_row) > 0 else [column]
                game["bombs"][str(next_row)] = new_bombs
                bombs_in_row = new_bombs
                await db.tower_games.update_one({"id": game["id"]}, {"$set": {"bombs": game["bombs"]}})
    else:
        # Make sure player's column is safe
        if column in bombs_in_row:
            # Move bomb to another position
            other_positions = [p for p in [1, 2, 3, 4] if p != column and p not in bombs_in_row]
            if other_positions:
                new_bomb_pos = random.choice(other_positions)
                new_bombs = [new_bomb_pos if b == column else b for b in bombs_in_row]
                game["bombs"][str(next_row)] = new_bombs
                bombs_in_row = new_bombs
                await db.tower_games.update_one({"id": game["id"]}, {"$set": {"bombs": game["bombs"]}})
    
    path = game["path"] + [{"row": next_row, "column": column}]
    
    if hit_bomb:
        # Game over - player lost
        await db.tower_games.update_one({"id": game["id"]}, {
            "$set": {"active": False, "current_row": next_row, "path": path, "win": 0}
        })
        await update_bank("tower", "lose", game["bet"], user)
        await calculate_raceback(user["id"], game["bet"])
        
        # Track RTP statistics for Tower (loss)
        await track_rtp_stat("tower", game["bet"], 0)
        
        # Check if cashback should be disabled
        await check_and_disable_cashback(user["id"])
        
        return {
            "success": True,
            "status": "lose",
            "row": next_row,
            "column": column,
            "bombs": game["bombs"],
            "message": "Бум! Вы наступили на бомбу"
        }
    else:
        # Safe step
        win = potential_win
        await db.tower_games.update_one({"id": game["id"]}, {
            "$set": {"current_row": next_row, "path": path, "win": win}
        })
        
        if next_row == 9:
            # Reached the top - auto cashout
            await db.tower_games.update_one({"id": game["id"]}, {"$set": {"active": False}})
            await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": win}})
            await update_bank("tower", "win", win - game["bet"], user)
            
            user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
            return {
                "success": True,
                "status": "win",
                "row": next_row,
                "column": column,
                "multiplier": multiplier,
                "win": win,
                "balance": user_data["balance"],
                "bombs": game["bombs"],
                "message": "Поздравляем! Вы достигли вершины!"
            }
        
        return {
            "success": True,
            "status": "continue",
            "row": next_row,
            "column": column,
            "multiplier": multiplier,
            "win": win,
            "path": path
        }

@api_router.post("/games/tower/cashout")
async def tower_cashout(user: dict = Depends(get_current_user)):
    """Cash out from Tower game"""
    game = await db.tower_games.find_one({"user_id": user["id"], "active": True}, {"_id": 0})
    if not game:
        raise HTTPException(status_code=400, detail="У вас нет активной игры")
    if game["current_row"] < 1:
        raise HTTPException(status_code=400, detail="Сделайте хотя бы один шаг")
    
    win = game["win"]
    if win <= 0:
        raise HTTPException(status_code=400, detail="Нечего забирать")
    
    await db.tower_games.update_one({"id": game["id"]}, {"$set": {"active": False}})
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": win}})
    await update_bank("tower", "win", win - game["bet"], user)
    await track_rtp_stat("tower", game["bet"], win)
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {
        "success": True,
        "win": win,
        "balance": user_data["balance"],
        "bombs": game["bombs"],
        "message": f"Вы забрали {win}₽!"
    }

@api_router.get("/games/tower/current")
async def tower_current(user: dict = Depends(get_current_user)):
    """Get current Tower game state"""
    game = await db.tower_games.find_one({"user_id": user["id"], "active": True}, {"_id": 0})
    if game:
        return {
            "success": True,
            "active": True,
            "bet": game["bet"],
            "difficulty": game["difficulty"],
            "current_row": game["current_row"],
            "path": game["path"],
            "win": game["win"]
        }
    return {"success": True, "active": False}

@api_router.get("/games/tower/config")
async def tower_config():
    """Get Tower game configuration"""
    return {
        "success": True,
        "difficulties": ["low", "medium", "high"],
        "rows": 9,
        "columns": 4,
        "multipliers": TOWER_MULTIPLIERS
    }

# ================== GAMES - CRASH ==================

@api_router.post("/games/crash/bet")
async def crash_bet(request: Request, user: dict = Depends(get_current_user), _=rate_limit("games")):
    """Place a bet for crash game - manual cashout"""
    data = await request.json()
    if user.get("is_ban"):
        raise HTTPException(status_code=403, detail="Ваш аккаунт заблокирован")
    
    # Anti-cheat check
    if not check_anti_cheat(user["id"], "crash", "bet"):
        raise HTTPException(status_code=429, detail="Слишком быстрые действия. Подождите немного.")
    
    bet = min(float(data.get("bet", 10)), user["balance"], 10000)
    
    if bet < 1:
        raise HTTPException(status_code=400, detail="Недостаточно средств")
    
    # Deduct bet immediately
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": -bet}})
    # Decrease wager properly (not below 0)
    await decrease_wager(user["id"], bet)
    
    settings = await get_settings()
    rtp = settings.get("crash_rtp", 97)
    
    # Generate crash point using cryptographically secure RNG
    # Formula based on house edge - lower RTP = more crashes at low multipliers
    house_edge = (100 - rtp) / 100  # e.g., 3% for RTP 97%, 20% for RTP 80%
    
    r = get_secure_random()
    
    # With probability = house_edge, instant crash at 1.00x
    if r < house_edge:
        crash_point = 1.0
    else:
        # Exponential distribution - lower crash points are more likely
        # Formula: crash_point = 1 / (1 - adjusted_random)
        # adjusted_random is scaled to [0, 0.99] to prevent infinity
        adjusted_r = (r - house_edge) / (1 - house_edge)
        
        # Scale by RTP factor to make lower RTP = lower crash points
        rtp_factor = rtp / 100
        max_random = 0.99 * rtp_factor  # Lower RTP = lower max random = lower crash points
        
        crash_point = 1.0 / (1 - adjusted_r * max_random)
    
    crash_point = round(min(crash_point, 1000), 2)
    crash_point = max(1.0, crash_point)
    
    # Save bet with pending status - crash_point is SECRET, only stored on server
    crash_bet_id = str(uuid.uuid4())
    await db.crash_bets.insert_one({
        "id": crash_bet_id,
        "user_id": user["id"],
        "bet": bet,
        "crash_point": crash_point,  # SECRET - never sent to client until game ends
        "status": "active",  # active, cashed_out, crashed
        "cashed_out_at": None,
        "win": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Get updated balance
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "balance": 1})
    
    # SECURITY: Do NOT send crash_point to client - it's revealed only after game ends
    return {
        "success": True,
        "bet_id": crash_bet_id,
        "balance": user_data["balance"],
        "message": "Ставка принята! Нажмите 'Забрать' во время полёта"
    }

@api_router.post("/games/crash/cashout/{bet_id}")
async def crash_cashout(bet_id: str, request: Request, user: dict = Depends(get_current_user), _=rate_limit("games")):
    """Manual cashout - player clicks button during flight"""
    data = await request.json()
    cashout_multiplier = float(data.get("multiplier", 1.0))
    
    # Anti-cheat: Validate multiplier is reasonable (not too precise for timing exploit)
    if cashout_multiplier != round(cashout_multiplier, 2):
        raise HTTPException(status_code=400, detail="Недопустимый множитель")
    
    # Find bet
    crash_bet = await db.crash_bets.find_one({"id": bet_id, "user_id": user["id"]}, {"_id": 0})
    if not crash_bet:
        raise HTTPException(status_code=404, detail="Ставка не найдена")
    
    # Log for debugging (remove in production)
    logging.info(f"Cashout attempt: bet_id={bet_id}, cashout_mult={cashout_multiplier}, server_crash_point={crash_bet['crash_point']}, status={crash_bet['status']}")
    
    if crash_bet["status"] != "active":
        raise HTTPException(status_code=400, detail="Ставка уже завершена")
    
    # Check if player cashed out before crash
    # IMPORTANT: Use < (strictly less) to allow cashout AT the crash point
    if cashout_multiplier > crash_bet["crash_point"]:
        # Too late! Crashed
        await db.crash_bets.update_one(
            {"id": bet_id},
            {"$set": {"status": "crashed", "win": 0}}
        )
        await update_bank("crash", "lose", crash_bet["bet"], user)
        await calculate_raceback(user["id"], crash_bet["bet"])
        await track_rtp_stat("crash", crash_bet["bet"], 0)
        
        # Check if cashback should be disabled
        await check_and_disable_cashback(user["id"])
        
        logging.info(f"Cashout FAILED: {cashout_multiplier} > {crash_bet['crash_point']}")
        
        user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "balance": 1})
        return {
            "success": False,
            "message": f"Слишком поздно! Краш на x{crash_bet['crash_point']}!",
            "status": "crashed",
            "balance": user_data["balance"]
        }
    
    # Success! Player cashed out in time
    win = round_money(crash_bet["bet"] * cashout_multiplier)
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": win}})
    await update_bank("crash", "win", win - crash_bet["bet"], user)
    await track_rtp_stat("crash", crash_bet["bet"], win)
    
    logging.info(f"Cashout SUCCESS: bet_id={bet_id}, mult={cashout_multiplier}, win={win}, crash_point={crash_bet['crash_point']}")
    
    # Update bet status
    await db.crash_bets.update_one(
        {"id": bet_id},
        {"$set": {
            "status": "cashed_out",
            "cashed_out_at": cashout_multiplier,
            "win": win
        }}
    )
    
    # Add to bets history
    await db.bets.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_name": user["name"],
        "game": "crash",
        "bet": crash_bet["bet"],
        "multiplier": cashout_multiplier,
        "win": win,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "balance": 1})
    
    return {
        "success": True,
        "status": "cashed_out",
        "multiplier": cashout_multiplier,
        "win": win,
        "balance": user_data["balance"],
        "message": f"Выигрыш: {win}₽ (x{cashout_multiplier})"
    }

@api_router.get("/games/crash/status/{bet_id}")
async def get_crash_status(bet_id: str, current_mult: float = 1.0, user: dict = Depends(get_current_user)):
    """Check crash bet status - called by frontend to know when crash happened
    
    If bet is still active and current_mult > crash_point, mark as lose
    """
    crash_bet = await db.crash_bets.find_one({"id": bet_id, "user_id": user["id"]}, {"_id": 0})
    if not crash_bet:
        raise HTTPException(status_code=404, detail="Ставка не найдена")
    
    # Auto-close bet if player passed crash point
    if crash_bet["status"] == "active" and current_mult > 0 and current_mult >= crash_bet["crash_point"]:
        # Mark as lose - player didn't cash out in time
        await db.crash_bets.update_one(
            {"id": bet_id},
            {"$set": {"status": "lose", "win": 0}}
        )
        await update_bank("crash", "lose", crash_bet["bet"], user)
        await calculate_raceback(user["id"], crash_bet["bet"])
        await track_rtp_stat("crash", crash_bet["bet"], 0)
        
        crash_bet["status"] = "lose"
        crash_bet["win"] = 0
        logging.info(f"Crash auto-close: bet {bet_id} lost at {crash_bet['crash_point']}x (current: {current_mult}x)")
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "balance": 1})
    
    return {
        "success": True,
        "status": crash_bet["status"],
        "crash_point": crash_bet["crash_point"],
        "cashed_out_at": crash_bet.get("cashed_out_at"),
        "win": crash_bet.get("win", 0),
        "balance": user_data["balance"]
    }

@api_router.get("/games/crash/history")
async def get_crash_history():
    """Get recent crash game results - REAL from database"""
    # Get last 20 completed crash rounds
    bets = await db.crash_bets.find(
        {"status": {"$in": ["win", "lose"]}},
        {"_id": 0, "crash_point": 1, "created_at": 1}
    ).sort("created_at", -1).limit(30).to_list(30)
    
    # Group by crash_point to get unique rounds (multiple players can play same round)
    seen_crashes = {}
    history = []
    
    for bet in bets:
        crash_point = bet["crash_point"]
        timestamp = bet.get("created_at", "")
        
        # Use crash_point + time window to identify unique rounds
        key = f"{crash_point}_{timestamp[:16]}"  # Group by minute
        
        if key not in seen_crashes:
            seen_crashes[key] = True
            history.append({"multiplier": crash_point})
            
            if len(history) >= 20:
                break
    
    # If not enough real data, add some generated history
    while len(history) < 20:
        r = random.random()
        if r < 0.3:
            mult = round(random.uniform(1.0, 1.9), 2)
        elif r < 0.6:
            mult = round(random.uniform(2.0, 5.0), 2)
        elif r < 0.85:
            mult = round(random.uniform(5.0, 10.0), 2)
        else:
            mult = round(random.uniform(10.0, 50.0), 2)
        history.append({"multiplier": mult})
    
    return {"success": True, "history": history[:20]}

@api_router.post("/games/crash/round-complete")
async def crash_round_complete(request: Request):
    """Save crash round to history (called by frontend after each crash)"""
    data = await request.json()
    crash_point = float(data.get("crash_point", 1.0))
    
    # Save to database as a system bet (no user)
    round_id = str(uuid.uuid4())
    await db.crash_bets.insert_one({
        "id": round_id,
        "user_id": "system",
        "bet": 0,
        "auto_cashout": 0,
        "crash_point": crash_point,
        "status": "lose",  # System round
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True, "crash_point": crash_point}

# ================== FAKE ONLINE ==================

@api_router.get("/online")
async def get_online_count():
    """Get fake online players count - never below 200"""
    base = 200
    variation = random.randint(0, 100)
    return {"success": True, "online": base + variation}

# ================== SUPPORT CHAT ==================

class SupportMessage(BaseModel):
    user_id: str
    message: str
    is_admin: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@api_router.post("/support/message")
async def send_support_message(request: Request, user: dict = Depends(get_current_user)):
    data = await request.json()
    message = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_name": user["name"],
        "message": data.get("message", ""),
        "is_admin": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    }
    await db.support_messages.insert_one(message)
    return {"success": True, "message_id": message["id"]}

@api_router.get("/support/messages")
async def get_support_messages(user: dict = Depends(get_current_user)):
    messages = await db.support_messages.find(
        {"user_id": user["id"]}, 
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return {"success": True, "messages": messages}

@api_router.get("/admin/support/chats")
async def get_support_chats(_ : bool = Depends(verify_admin_token)):
    # Get unique user conversations with registration_number
    pipeline = [
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$user_id",
            "user_name": {"$first": "$user_name"},
            "last_message": {"$first": "$message"},
            "last_time": {"$first": "$created_at"},
            "unread_count": {"$sum": {"$cond": [{"$and": [{"$eq": ["$read", False]}, {"$eq": ["$is_admin", False]}]}, 1, 0]}}
        }},
        # Lookup user to get registration_number
        {"$lookup": {
            "from": "users",
            "localField": "_id",
            "foreignField": "id",
            "as": "user_info"
        }},
        {"$addFields": {
            "registration_number": {"$arrayElemAt": ["$user_info.registration_number", 0]},
            "user_balance": {"$arrayElemAt": ["$user_info.balance", 0]},
            "user_deposit": {"$arrayElemAt": ["$user_info.deposit", 0]}
        }},
        {"$project": {
            "user_info": 0  # Remove the full user_info array
        }},
        {"$sort": {"last_time": -1}}
    ]
    chats = await db.support_messages.aggregate(pipeline).to_list(100)
    return {"success": True, "chats": chats}

@api_router.get("/admin/support/messages/{user_id}")
async def get_user_support_messages(user_id: str, _ : bool = Depends(verify_admin_token)):
    messages = await db.support_messages.find(
        {"user_id": user_id}, 
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    # Mark as read
    await db.support_messages.update_many(
        {"user_id": user_id, "is_admin": False},
        {"$set": {"read": True}}
    )
    return {"success": True, "messages": messages}

@api_router.post("/admin/support/reply/{user_id}")
async def admin_reply_support(user_id: str, request: Request, _ : bool = Depends(verify_admin_token)):
    data = await request.json()
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "name": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    message = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_name": user["name"],
        "message": data.get("message", ""),
        "is_admin": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    }
    await db.support_messages.insert_one(message)
    return {"success": True, "message_id": message["id"]}

# ================== GAMES - X100 ==================

X100_WHEEL = [
    2, 3, 2, 15, 2, 3, 2, 20, 2, 15, 2, 3, 2, 3, 2, 15, 2, 3, 10, 3, 2, 10, 2, 3, 2,
    100,  # Jackpot position
    2, 3, 2, 10, 2, 3, 2, 3, 2, 15, 2, 3, 2, 3, 2, 20, 2, 3, 2, 10, 2, 3, 2, 10,
    2, 3, 2, 15, 2, 3, 2, 3, 2, 10, 20, 3, 2, 3, 2, 15, 2, 10, 2, 3, 2, 20, 2, 3, 2,
    15, 2, 3, 2, 10, 2, 3, 2, 3, 2, 10, 2, 3, 2, 3, 2, 10, 2, 3, 2, 3, 2, 3, 2
]

@api_router.post("/games/x100/play")
async def x100_play(request: Request, user: dict = Depends(get_current_user), _=rate_limit("games")):
    data = await request.json()
    if user.get("is_ban"):
        raise HTTPException(status_code=403, detail="Ваш аккаунт заблокирован")
    
    # Anti-cheat check
    if not check_anti_cheat(user["id"], "x100", "play"):
        raise HTTPException(status_code=429, detail="Слишком быстрые действия. Подождите немного.")
    
    bet = min(float(data.get("bet", 10)), user["balance"], MAX_BET)
    selected_coef = int(data.get("coef", 2))  # Player selects coefficient: 2, 3, 10, 15, 20, or 100
    
    valid_coefs = [2, 3, 10, 15, 20, 100]
    if selected_coef not in valid_coefs:
        raise HTTPException(status_code=400, detail="Неверный множитель")
    
    if bet < 1:
        raise HTTPException(status_code=400, detail="Недостаточно средств")
    
    settings = await get_settings()
    rtp = settings.get("x100_rtp", 97)
    
    # First determine if player should win based on RTP
    # Use selected coefficient as multiplier for RTP calculation
    player_wins = user.get("is_youtuber") or should_player_win(rtp, user, selected_coef, "x100")
    
    if player_wins:
        # Find all positions with player's selected coefficient
        winning_positions = [i for i, c in enumerate(X100_WHEEL) if c == selected_coef]
        if winning_positions:
            position = random.choice(winning_positions)
        else:
            position = random.randint(0, len(X100_WHEEL) - 1)
    else:
        # Find all positions WITHOUT player's selected coefficient
        losing_positions = [i for i, c in enumerate(X100_WHEEL) if c != selected_coef]
        position = random.choice(losing_positions)
    
    result_coef = X100_WHEEL[position]
    is_win = result_coef == selected_coef
    
    if is_win:
        win = round_money(bet * selected_coef)
        balance_change = win - bet
    else:
        win = 0
        balance_change = -bet
        await calculate_raceback(user["id"], bet)
    
    # Update balance
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": balance_change}})
    # Decrease wager properly (not below 0)
    await decrease_wager(user["id"], bet)
    
    # Track RTP statistics for X100
    await track_rtp_stat("x100", bet, win if is_win else 0)
    
    # Save game to history
    await db.x100_games.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "bet": bet,
        "selected_coef": selected_coef,
        "result_coef": result_coef,
        "win": win,
        "coef": result_coef if is_win else 0,
        "status": "win" if is_win else "lose",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Calculate rotation angle for animation
    segment_angle = 360 / len(X100_WHEEL)
    rotation = position * segment_angle + (360 * 5)  # 5 full rotations + final position
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {
        "success": True, "status": "win" if is_win else "lose",
        "selected_coef": selected_coef, "result_coef": result_coef,
        "position": position, "rotation": rotation,
        "win": win, "balance": user_data["balance"]
    }

# ================== GAMES - KENO ==================

@api_router.post("/games/keno/play")
async def keno_play(request: Request, user: dict = Depends(get_current_user)):
    data = await request.json()
    if user.get("is_ban"):
        raise HTTPException(status_code=403, detail="Ваш аккаунт заблокирован")
    
    bet = min(float(data.get("bet", 10)), user["balance"], MAX_BET)
    selected_numbers = data.get("numbers", [])  # Player selects 1-10 numbers from 1-40
    
    if not selected_numbers or len(selected_numbers) < 1 or len(selected_numbers) > 10:
        raise HTTPException(status_code=400, detail="Выберите от 1 до 10 чисел")
    
    if any(n < 1 or n > 40 for n in selected_numbers):
        raise HTTPException(status_code=400, detail="Числа должны быть от 1 до 40")
    
    if bet < 1:
        raise HTTPException(status_code=400, detail="Недостаточно средств")
    
    settings = await get_settings()
    rtp = settings.get("keno_rtp", 97)
    
    # Draw 10 random numbers
    drawn_numbers = random.sample(range(1, 41), 10)
    
    # Count matches
    matches = len(set(selected_numbers) & set(drawn_numbers))
    
    # Keno payout table based on selections and matches
    payouts = {
        1: {1: 3},
        2: {2: 9},
        3: {2: 2, 3: 25},
        4: {2: 1, 3: 5, 4: 50},
        5: {3: 3, 4: 15, 5: 100},
        6: {3: 2, 4: 5, 5: 30, 6: 200},
        7: {4: 3, 5: 10, 6: 50, 7: 500},
        8: {4: 2, 5: 5, 6: 20, 7: 100, 8: 1000},
        9: {5: 3, 6: 10, 7: 30, 8: 300, 9: 2000},
        10: {5: 2, 6: 5, 7: 15, 8: 100, 9: 500, 10: 5000}
    }
    
    multiplier = payouts.get(len(selected_numbers), {}).get(matches, 0)
    win = round_money(bet * multiplier) if multiplier > 0 else 0
    
    # Apply RTP adjustment with multiplier
    if win > 0 and not user.get("is_youtuber") and not should_player_win(rtp, user, multiplier if multiplier > 0 else 2.0, "keno"):
        # Reduce matches to lose
        drawn_numbers = [n for n in range(1, 41) if n not in selected_numbers][:10]
        matches = 0
        win = 0
    
    balance_change = win - bet if win > 0 else -bet
    # Update balance
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": balance_change}})
    # Decrease wager properly (not below 0)
    await decrease_wager(user["id"], bet)
    
    # Track RTP statistics for Keno
    await track_rtp_stat("keno", bet, win)
    
    if win == 0:
        await calculate_raceback(user["id"], bet)
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {
        "success": True, "status": "win" if win > 0 else "lose",
        "selected": selected_numbers, "drawn": drawn_numbers,
        "matches": matches, "multiplier": multiplier,
        "win": win, "balance": user_data["balance"]
    }

# ================== REFERRAL ==================

@api_router.get("/ref/stats")
async def get_ref_stats(user: dict = Depends(get_current_user)):
    deposited_refs = user.get("deposited_refs", 0)
    current_level = get_ref_level(deposited_refs)
    
    # Find next level
    next_level = None
    for i, level in enumerate(REF_LEVELS):
        if level["min_refs"] > deposited_refs:
            next_level = level
            break
    
    return {
        "success": True, 
        "ref_link": user["ref_link"], 
        "referalov": user["referalov"], 
        "deposited_refs": deposited_refs,
        "income": user["income"], 
        "income_all": user["income_all"],
        "is_demo": user.get("is_demo", False),
        "level": current_level,
        "next_level": next_level,
        "levels": REF_LEVELS
    }

@api_router.get("/ref/list")
async def get_referrals_list(user: dict = Depends(get_current_user)):
    """Get list of user's referrals with their deposit info"""
    # Find all users who were invited by this user (using ref_link)
    referrals = await db.users.find(
        {"invited_by": user["ref_link"]},  # Search by ref_link, not ID
        {"_id": 0, "id": 1, "name": 1, "username": 1, "created_at": 1, "total_deposited": 1, "deposit": 1}
    ).sort("created_at", -1).limit(100).to_list(100)
    
    # Format referrals data
    formatted_refs = []
    for ref in referrals:
        formatted_refs.append({
            "id": ref["id"][:8] + "...",  # Shortened ID for privacy
            "name": ref.get("name", "Игрок"),
            "username": ref.get("username", ""),
            "registered": ref.get("created_at", ""),
            "total_deposited": ref.get("total_deposited", 0) or ref.get("deposit", 0),
            "has_deposited": (ref.get("total_deposited", 0) or ref.get("deposit", 0)) > 0
        })
    
    return {
        "success": True,
        "referrals": formatted_refs,
        "total_count": user.get("referalov", 0),
        "deposited_count": user.get("deposited_refs", 0)
    }

@api_router.post("/ref/withdraw")
async def ref_withdraw(user: dict = Depends(get_current_user)):
    # Demo users cannot withdraw referral income
    if user.get("is_demo"):
        raise HTTPException(status_code=403, detail="Реферальная система недоступна в демо-режиме. Авторизуйтесь через Telegram.")
    
    # Check if user has deposit this month
    has_deposit = await check_user_has_deposit_this_month(user["id"])
    if not has_deposit:
        raise HTTPException(status_code=400, detail="Для вывода бонусов необходим хотя бы один депозит за текущий месяц (минимум 150₽)")
    
    if user["income"] < 150:
        raise HTTPException(status_code=400, detail="Минимум для вывода - 150 рублей")
    income = user["income"]
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": income}, "$set": {"income": 0}})
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"success": True, "withdrawn": income, "balance": user_data["balance"]}

# ================== RACEBACK ==================

@api_router.get("/bonus/raceback")
async def get_raceback(user: dict = Depends(get_current_user)):
    """Get cashback info with level system."""
    total_deposited = user.get("total_deposited", 0)
    current_level = get_cashback_level(total_deposited)
    
    # Find next level
    next_level = None
    for level in CASHBACK_LEVELS:
        if level["min_deposit"] > total_deposited:
            next_level = level
            break
    
    return {
        "success": True, 
        "raceback": user.get("raceback", 0),
        "total_deposited": total_deposited,
        "level": current_level,
        "next_level": next_level,
        "levels": CASHBACK_LEVELS,
        "info": "Кешбек начисляется при каждом депозите. Забрать можно при нулевом балансе."
    }

@api_router.post("/bonus/raceback/claim")
async def claim_raceback(user: dict = Depends(get_current_user)):
    # Demo users cannot claim cashback
    if user.get("is_demo"):
        raise HTTPException(status_code=403, detail="Кешбэк недоступен в демо-режиме. Авторизуйтесь через Telegram.")
    
    # Check if user has deposit this month
    has_deposit = await check_user_has_deposit_this_month(user["id"])
    if not has_deposit:
        raise HTTPException(status_code=400, detail="Для получения кешбэка необходим хотя бы один депозит за текущий месяц (минимум 150₽)")
    
    if user["balance"] > 0:
        raise HTTPException(status_code=400, detail="Кешбэк доступен только при нулевом балансе")
    if user["raceback"] < 1:
        raise HTTPException(status_code=400, detail="Недостаточно кешбэка")
    
    raceback = user["raceback"]
    
    # Transfer cashback to balance
    await db.users.update_one(
        {"id": user["id"]}, 
        {
            "$inc": {"balance": raceback, "deposit_balance": raceback},
            "$set": {"raceback": 0}
        }
    )
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"success": True, "claimed": raceback, "balance": user_data["balance"]}

# ================== DAILY BONUS ==================

# Daily bonus rewards (day streak -> bonus amount)
DAILY_BONUS_REWARDS = {
    1: 2,     # Day 1: 2₽
    2: 4,     # Day 2: 4₽
    3: 6,     # Day 3: 6₽
    4: 10,    # Day 4: 10₽
    5: 15,    # Day 5: 15₽
    6: 20,    # Day 6: 20₽
    7: 35,    # Day 7: 35₽ (weekly bonus!)
}

@api_router.get("/bonus/daily")
async def get_daily_bonus(user: dict = Depends(get_current_user)):
    """Get daily bonus status"""
    if user.get("is_demo"):
        return {
            "success": True, "is_demo": True,
            "can_claim": False, "streak": 0, "next_bonus": 10,
            "message": "Ежедневный бонус недоступен в демо-режиме"
        }
    
    last_claim = user.get("last_daily_claim")
    streak = user.get("daily_streak", 0)
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    can_claim = False
    if not last_claim:
        can_claim = True
        streak = 0
    else:
        last_claim_date = datetime.fromisoformat(last_claim.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        last_claim_day = last_claim_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        days_since_claim = (today - last_claim_day).days
        
        if days_since_claim >= 1:
            can_claim = True
            if days_since_claim > 1:
                # Streak broken - reset to 0
                streak = 0
    
    next_day = (streak % 7) + 1 if streak > 0 else 1
    next_bonus = DAILY_BONUS_REWARDS.get(next_day, 10)
    
    return {
        "success": True,
        "can_claim": can_claim,
        "streak": streak,
        "next_day": next_day,
        "next_bonus": next_bonus,
        "rewards": DAILY_BONUS_REWARDS
    }

@api_router.post("/bonus/daily/claim")
async def claim_daily_bonus(user: dict = Depends(get_current_user)):
    """Claim daily bonus"""
    if user.get("is_demo"):
        raise HTTPException(status_code=403, detail="Ежедневный бонус недоступен в демо-режиме. Авторизуйтесь через Telegram.")
    
    # Check if user has deposit this month
    has_deposit = await check_user_has_deposit_this_month(user["id"])
    if not has_deposit:
        raise HTTPException(status_code=400, detail="Для получения ежедневного бонуса необходим хотя бы один депозит за текущий месяц (минимум 150₽)")
    
    last_claim = user.get("last_daily_claim")
    streak = user.get("daily_streak", 0)
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Check if already claimed today
    if last_claim:
        last_claim_date = datetime.fromisoformat(last_claim.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        last_claim_day = last_claim_date.replace(hour=0, minute=0, second=0, microsecond=0)
        days_since_claim = (today - last_claim_day).days
        
        if days_since_claim < 1:
            raise HTTPException(status_code=400, detail="Вы уже получили бонус сегодня. Приходите завтра!")
        
        if days_since_claim > 1:
            streak = 0  # Reset streak if missed a day
    
    # Calculate new streak and bonus
    new_streak = streak + 1
    day_in_week = ((new_streak - 1) % 7) + 1  # 1-7 cycling
    bonus = DAILY_BONUS_REWARDS.get(day_in_week, 10)
    
    # Add wager requirement (1x bonus)
    wager_increase = bonus
    
    await db.users.update_one(
        {"id": user["id"]}, 
        {
            "$inc": {"balance": bonus, "wager": wager_increase},
            "$set": {
                "last_daily_claim": now.isoformat(),
                "daily_streak": new_streak
            }
        }
    )
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    return {
        "success": True,
        "bonus": bonus,
        "streak": new_streak,
        "day": day_in_week,
        "balance": user_data["balance"],
        "wager": user_data["wager"],
        "message": f"Бонус {bonus}₽ получен! День {day_in_week}/7"
    }

# ================== ACHIEVEMENTS ==================

ACHIEVEMENTS = {
    "first_win": {"name": "Первая победа", "desc": "Выиграйте первую игру", "reward": 5, "icon": "fa-trophy", "type": "first_win"},
    "high_roller": {"name": "Хайроллер", "desc": "Сделайте ставку 500₽+", "reward": 12, "icon": "fa-coins", "type": "high_bet", "target": 500},
    "lucky_streak": {"name": "Удачная серия", "desc": "Выиграйте 5 игр подряд", "reward": 25, "icon": "fa-fire", "type": "win_streak", "target": 5},
    "big_win": {"name": "Большой выигрыш", "desc": "Выиграйте 500₽ за раз", "reward": 17, "icon": "fa-star", "type": "big_win", "target": 500},
    "explorer": {"name": "Исследователь", "desc": "Сыграйте во все игры", "reward": 7, "icon": "fa-compass", "type": "all_games"},
    "veteran": {"name": "Ветеран", "desc": "Сделайте 100 ставок", "reward": 37, "icon": "fa-medal", "type": "total_bets", "target": 100},
    "week_streak": {"name": "Недельная серия", "desc": "Заходите 7 дней подряд", "reward": 50, "icon": "fa-calendar-check", "type": "daily_streak", "target": 7},
}

async def check_achievements(user_id: str) -> list:
    """Check and unlock achievements for user"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return []
    
    unlocked = user.get("achievements", [])
    new_achievements = []
    
    # Get all games from all collections
    game_collections = ["mines_games", "dice_games", "bubbles_games", "tower_games", "crash_games", "x100_games"]
    
    total_games = 0
    total_wins = 0
    max_win = 0
    max_bet = 0
    games_played_set = set()
    current_win_streak = 0
    max_win_streak = 0
    
    for collection_name in game_collections:
        collection = db[collection_name]
        games = await collection.find({"user_id": user_id}).sort("created_at", 1).to_list(10000)
        
        game_type = collection_name.replace("_games", "")
        
        for game in games:
            total_games += 1
            bet = game.get("bet", 0)
            win = game.get("win", 0)
            status = game.get("status", "")
            
            if bet > max_bet:
                max_bet = bet
            
            if win > max_win:
                max_win = win
                
            games_played_set.add(game_type)
            
            if status == "win":
                total_wins += 1
                current_win_streak += 1
                if current_win_streak > max_win_streak:
                    max_win_streak = current_win_streak
            else:
                current_win_streak = 0
    
    # Check each achievement
    # first_win - выиграйте первую игру
    if "first_win" not in unlocked and total_wins >= 1:
        new_achievements.append("first_win")
    
    # high_roller - ставка 500₽+
    if "high_roller" not in unlocked and max_bet >= 500:
        new_achievements.append("high_roller")
    
    # lucky_streak - 5 побед подряд
    if "lucky_streak" not in unlocked and max_win_streak >= 5:
        new_achievements.append("lucky_streak")
    
    # big_win - выигрыш 500₽ за раз
    if "big_win" not in unlocked and max_win >= 500:
        new_achievements.append("big_win")
    
    # explorer - сыграть во все игры (6 игр)
    if "explorer" not in unlocked and len(games_played_set) >= 6:
        new_achievements.append("explorer")
    
    # veteran - 100 ставок
    if "veteran" not in unlocked and total_games >= 100:
        new_achievements.append("veteran")
    
    # week_streak - 7 дней подряд (проверяем daily_streak пользователя)
    if "week_streak" not in unlocked and user.get("daily_streak", 0) >= 7:
        new_achievements.append("week_streak")
    
    # Save new achievements
    if new_achievements:
        await db.users.update_one(
            {"id": user_id},
            {"$push": {"achievements": {"$each": new_achievements}}}
        )
    
    return new_achievements

@api_router.get("/achievements")
async def get_achievements(user: dict = Depends(get_current_user)):
    """Get user achievements with real-time check"""
    if user.get("is_demo"):
        # For demo users, return empty achievements
        achievements_list = []
        for key, data in ACHIEVEMENTS.items():
            achievements_list.append({
                "id": key,
                "name": data["name"],
                "desc": data["desc"],
                "reward": data["reward"],
                "icon": data["icon"],
                "unlocked": False,
                "claimed": False
            })
        return {"success": True, "achievements": achievements_list, "is_demo": True}
    
    # Check for new achievements
    await check_achievements(user["id"])
    
    # Refresh user data
    user = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    user_achievements = user.get("achievements", [])
    claimed_achievements = user.get("claimed_achievements", [])
    
    achievements_list = []
    for key, data in ACHIEVEMENTS.items():
        achievements_list.append({
            "id": key,
            "name": data["name"],
            "desc": data["desc"],
            "reward": data["reward"],
            "icon": data["icon"],
            "unlocked": key in user_achievements,
            "claimed": key in claimed_achievements
        })
    
    return {"success": True, "achievements": achievements_list}

@api_router.post("/achievements/{achievement_id}/claim")
async def claim_achievement(achievement_id: str, user: dict = Depends(get_current_user)):
    """Claim achievement reward"""
    if user.get("is_demo"):
        raise HTTPException(status_code=403, detail="Достижения недоступны в демо-режиме.")
    
    # Check if user has deposit this month
    has_deposit = await check_user_has_deposit_this_month(user["id"])
    if not has_deposit:
        raise HTTPException(status_code=400, detail="Для получения награды за достижение необходим хотя бы один депозит за текущий месяц (минимум 150₽)")
    
    if achievement_id not in ACHIEVEMENTS:
        raise HTTPException(status_code=404, detail="Достижение не найдено")
    
    user_achievements = user.get("achievements", [])
    claimed_achievements = user.get("claimed_achievements", [])
    
    if achievement_id not in user_achievements:
        raise HTTPException(status_code=400, detail="Достижение не разблокировано")
    
    if achievement_id in claimed_achievements:
        raise HTTPException(status_code=400, detail="Награда уже получена")
    
    reward = ACHIEVEMENTS[achievement_id]["reward"]
    
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$inc": {"balance": reward},
            "$push": {"claimed_achievements": achievement_id}
        }
    )
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    return {
        "success": True,
        "achievement": ACHIEVEMENTS[achievement_id]["name"],
        "reward": reward,
        "balance": user_data["balance"]
    }

# ================== DAILY TASKS ==================

DAILY_TASKS = {
    "play_3_games": {
        "name": "Активный игрок",
        "desc": "Сыграйте 3 игры сегодня",
        "reward": 3,
        "icon": "fa-gamepad",
        "target": 3,
        "type": "games_played"
    },
    "win_any_game": {
        "name": "Победитель",
        "desc": "Выиграйте хотя бы 1 игру",
        "reward": 2,
        "icon": "fa-trophy",
        "target": 1,
        "type": "games_won"
    },
    "bet_100": {
        "name": "Ставочник",
        "desc": "Сделайте ставки на сумму 100₽",
        "reward": 5,
        "icon": "fa-coins",
        "target": 100,
        "type": "total_bet"
    },
    "play_2_different": {
        "name": "Разнообразие",
        "desc": "Сыграйте в 2 разные игры",
        "reward": 3,
        "icon": "fa-dice",
        "target": 2,
        "type": "different_games"
    },
    "win_50": {
        "name": "Профит",
        "desc": "Выиграйте 50₽ за день",
        "reward": 6,
        "icon": "fa-money-bill-wave",
        "target": 50,
        "type": "total_win"
    }
}

async def get_daily_task_progress(user_id: str):
    """Get user's progress on daily tasks"""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = today.isoformat()
    
    # Get all games played today from all game collections
    game_collections = ["mines_games", "dice_games", "bubbles_games", "tower_games", "crash_games", "x100_games"]
    
    games_played = 0
    games_won = 0
    total_bet = 0
    total_win = 0
    games_set = set()
    
    for collection_name in game_collections:
        collection = db[collection_name]
        games = await collection.find({
            "user_id": user_id,
            "created_at": {"$gte": today_str}
        }).to_list(1000)
        
        game_type = collection_name.replace("_games", "")
        
        for game in games:
            games_played += 1
            total_bet += game.get("bet", 0)
            games_set.add(game_type)
            
            if game.get("status") == "win":
                games_won += 1
                total_win += game.get("win", 0)
    
    return {
        "games_played": games_played,
        "games_won": games_won,
        "total_bet": total_bet,
        "total_win": total_win,
        "different_games": len(games_set)
    }

@api_router.get("/tasks/daily")
async def get_daily_tasks(user: dict = Depends(get_current_user)):
    """Get daily tasks and their progress"""
    if user.get("is_demo"):
        return {
            "success": True,
            "is_demo": True,
            "tasks": [],
            "message": "Задания недоступны в демо-режиме"
        }
    
    # Get today's claimed tasks
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    claimed_today = user.get("daily_tasks_claimed", {}).get(today, [])
    
    # Get progress
    progress = await get_daily_task_progress(user["id"])
    
    tasks_list = []
    for task_id, task_data in DAILY_TASKS.items():
        task_type = task_data["type"]
        current = progress.get(task_type, 0)
        target = task_data["target"]
        completed = current >= target
        claimed = task_id in claimed_today
        
        tasks_list.append({
            "id": task_id,
            "name": task_data["name"],
            "desc": task_data["desc"],
            "reward": task_data["reward"],
            "icon": task_data["icon"],
            "current": min(current, target),
            "target": target,
            "completed": completed,
            "claimed": claimed
        })
    
    return {"success": True, "tasks": tasks_list}

@api_router.post("/tasks/daily/{task_id}/claim")
async def claim_daily_task(task_id: str, user: dict = Depends(get_current_user)):
    """Claim daily task reward"""
    if user.get("is_demo"):
        raise HTTPException(status_code=403, detail="Задания недоступны в демо-режиме")
    
    # Check if user has deposit this month
    has_deposit = await check_user_has_deposit_this_month(user["id"])
    if not has_deposit:
        raise HTTPException(status_code=400, detail="Для получения награды за задание необходим хотя бы один депозит за текущий месяц (минимум 150₽)")
    
    if task_id not in DAILY_TASKS:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    
    # Get today's claimed tasks
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    claimed_today = user.get("daily_tasks_claimed", {}).get(today, [])
    
    if task_id in claimed_today:
        raise HTTPException(status_code=400, detail="Награда уже получена сегодня")
    
    # Check if task is completed
    progress = await get_daily_task_progress(user["id"])
    task_data = DAILY_TASKS[task_id]
    current = progress.get(task_data["type"], 0)
    
    if current < task_data["target"]:
        raise HTTPException(status_code=400, detail=f"Задание не выполнено: {current}/{task_data['target']}")
    
    reward = task_data["reward"]
    
    # Update user - add reward and mark task as claimed
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$inc": {"balance": reward},
            "$set": {f"daily_tasks_claimed.{today}": claimed_today + [task_id]}
        }
    )
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    return {
        "success": True,
        "task": task_data["name"],
        "reward": reward,
        "balance": user_data["balance"],
        "message": f"Получено {reward}₽ за задание «{task_data['name']}»"
    }

# ================== PLAYERS CHAT ==================

@api_router.get("/chat/messages")
async def get_chat_messages(limit: int = 50):
    """Get recent chat messages"""
    messages = await db.chat_messages.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"success": True, "messages": list(reversed(messages))}

@api_router.post("/chat/send")
async def send_chat_message(request: Request, user: dict = Depends(get_current_user)):
    """Send message to players chat"""
    data = await request.json()
    text = data.get("text", "").strip()
    
    if not text:
        raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")
    if len(text) > 500:
        raise HTTPException(status_code=400, detail="Сообщение слишком длинное")
    
    # Check for commands
    if text.startswith("/"):
        return await handle_chat_command(text, user)
    
    # Regular message
    message = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_name": user.get("name", "Игрок"),
        "user_reg_number": user.get("registration_number"),  # NEW: For support identification
        "text": text,
        "type": "message",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.chat_messages.insert_one(message)
    
    return {"success": True, "message": message}

async def handle_chat_command(text: str, user: dict) -> dict:
    """Handle chat commands"""
    parts = text.lower().split()
    command = parts[0]
    
    if command == "/stats" or command == "/статистика":
        # Get user stats
        total_deposits = await db.payments.count_documents({"user_id": user["id"], "status": "completed"})
        total_withdraws = await db.withdraws.count_documents({"user_id": user["id"], "status": "completed"})
        deposit_sum = 0
        withdraw_sum = 0
        
        async for p in db.payments.find({"user_id": user["id"], "status": "completed"}):
            deposit_sum += p.get("amount", 0)
        async for w in db.withdraws.find({"user_id": user["id"], "status": "completed"}):
            withdraw_sum += w.get("amount", 0)
        
        response_text = f"📊 Статистика {user.get('name', 'Игрок')}:\n💰 Депозитов: {total_deposits} ({deposit_sum:.2f}₽)\n💸 Выводов: {total_withdraws} ({withdraw_sum:.2f}₽)\n💵 Баланс: {user['balance']:.2f}₽"
        
        message = {
            "id": str(uuid.uuid4()),
            "user_id": "system",
            "user_name": "🤖 Бот",
            "text": response_text,
            "type": "system",
            "private_for": user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_messages.insert_one(message)
        return {"success": True, "message": message}
    
    elif command == "/send" or command == "/отправить":
        # Send money to another player
        if len(parts) < 3:
            return {"success": False, "error": "Использование: /send @имя сумма"}
        
        # CHECK: Запретить отправку если есть вейджер
        if user.get("wager", 0) > 0:
            return {"success": False, "error": f"❌ Нельзя отправлять деньги пока есть вейджер ({user['wager']:.2f}₽). Отыграйте вейджер сначала!"}
        
        recipient_name = parts[1].replace("@", "")
        try:
            amount = float(parts[2])
        except:
            return {"success": False, "error": "Неверная сумма"}
        
        if amount < 1:
            return {"success": False, "error": "Минимальная сумма 1₽"}
        if amount > user["balance"]:
            return {"success": False, "error": "Недостаточно средств"}
        
        # Find recipient
        recipient = await db.users.find_one({"name": {"$regex": f"^{recipient_name}$", "$options": "i"}}, {"_id": 0})
        if not recipient:
            return {"success": False, "error": f"Пользователь {recipient_name} не найден"}
        if recipient["id"] == user["id"]:
            return {"success": False, "error": "Нельзя отправить себе"}
        
        # Transfer money
        await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": -amount}})
        await db.users.update_one({"id": recipient["id"]}, {"$inc": {"balance": amount}})
        
        # Log transfer
        await db.transfers.insert_one({
            "id": str(uuid.uuid4()),
            "from_user": user["id"],
            "to_user": recipient["id"],
            "amount": amount,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        message = {
            "id": str(uuid.uuid4()),
            "user_id": "system",
            "user_name": "🤖 Бот",
            "text": f"💸 {user.get('name', 'Игрок')} отправил {amount:.2f}₽ игроку {recipient.get('name', 'Игрок')}",
            "type": "transfer",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_messages.insert_one(message)
        
        user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
        return {"success": True, "message": message, "balance": user_data["balance"]}
    
    elif command == "/request" or command == "/запрос":
        # Request money
        if len(parts) < 2:
            return {"success": False, "error": "Использование: /request сумма"}
        
        try:
            amount = float(parts[1])
        except:
            return {"success": False, "error": "Неверная сумма"}
        
        message = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "user_name": user.get("name", "Игрок"),
            "text": f"🙏 Запрашивает {amount:.2f}₽",
            "type": "request",
            "request_amount": amount,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_messages.insert_one(message)
        return {"success": True, "message": message}
    
    elif command == "/help" or command == "/помощь":
        help_text = """📋 Команды чата:
/stats - Ваша статистика
/send @имя сумма - Отправить деньги
/request сумма - Запросить деньги
/help - Показать команды"""
        
        message = {
            "id": str(uuid.uuid4()),
            "user_id": "system",
            "user_name": "🤖 Бот",
            "text": help_text,
            "type": "system",
            "private_for": user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_messages.insert_one(message)
        return {"success": True, "message": message}
    
    return {"success": False, "error": "Неизвестная команда. Напишите /help"}

# ================== PAYMENTS ==================

# Payment providers configuration
ONEPLATPAY_BASE_URL = os.environ.get('ONEPLATPAY_BASE_URL', 'https://1plat.cash')
ONEPLATPAY_SHOP_ID = os.environ.get('ONEPLATPAY_SHOP_ID', '')
ONEPLATPAY_SECRET = os.environ.get('ONEPLATPAY_SECRET', '')

P2PARADISE_BASE_URL = os.environ.get('P2PARADISE_BASE_URL', 'https://p2paradise.net')
P2PARADISE_API_KEY = os.environ.get('P2PARADISE_API_KEY', '')
P2PARADISE_MERCHANT_ID = '1'  # Will be set from API response

CRYPTOBOT_BASE_URL = os.environ.get('CRYPTOBOT_BASE_URL', 'https://pay.crypt.bot')
CRYPTOBOT_TOKEN = os.environ.get('CRYPTOBOT_TOKEN', '')

CRYPTOCLOUD_BASE_URL = 'https://api.cryptocloud.plus/v2'
CRYPTOCLOUD_API_KEY = os.environ.get('CRYPTOCLOUD_API_KEY', '')
CRYPTOCLOUD_SHOP_ID = os.environ.get('CRYPTOCLOUD_SHOP_ID', '')

# NicePay configuration
NICEPAY_BASE_URL = 'https://nicepay.io/public/api'
NICEPAY_MERCHANT_ID = os.environ.get('NICEPAY_MERCHANT_ID', '')
NICEPAY_SECRET = os.environ.get('NICEPAY_SECRET', '')

# Payment system availability
def get_available_providers():
    providers = []
    # NicePay as primary for cards/SBP (has auto-payouts)
    if NICEPAY_MERCHANT_ID and NICEPAY_SECRET:
        providers.append({
            "id": "nicepay",
            "name": "Карты/СБП",
            "methods": ["sbp", "card", "sberbank", "tinkoff"],
            "icon": "fa-credit-card",
            "priority": 1
        })
    if ONEPLATPAY_SHOP_ID and ONEPLATPAY_SECRET:
        providers.append({
            "id": "1plat",
            "name": "Карты/СБП #2",
            "methods": ["sbp", "card"],
            "icon": "fa-credit-card",
            "priority": 2
        })
    if P2PARADISE_API_KEY:
        providers.append({
            "id": "p2paradise",
            "name": "Карты/СБП #3",
            "methods": ["sbp", "card", "sbp-card"],
            "icon": "fa-money-bill-transfer",
            "priority": 3
        })
    if CRYPTOBOT_TOKEN:
        providers.append({
            "id": "cryptobot",
            "name": "Crypto Bot",
            "methods": ["USDT", "TON", "BTC", "ETH"],
            "icon": "fa-telegram",
            "priority": 10
        })
    if CRYPTOCLOUD_API_KEY:
        providers.append({
            "id": "cryptocloud",
            "name": "Crypto",
            "methods": ["USDT", "BTC", "ETH", "LTC", "DOGE", "TRX", "XRP", "BNB", "SOL", "MATIC", "AVAX", "DASH", "XMR", "SHIB"],
            "icon": "fa-bitcoin",
            "priority": 11
        })
    # Admin deposit option - always available
    providers.append({
        "id": "admin",
        "name": "Через администратора",
        "methods": ["admin"],
        "icon": "fa-user-shield",
        "priority": 99,
        "description": "Пополнение от 150₽ до 250,000₽",
        "contact": "@easymoneysupportvip",
        "min_amount": 150,
        "max_amount": 250000
    })
    # Sort by priority
    providers.sort(key=lambda x: x.get("priority", 99))
    return providers

def is_payment_configured():
    return len(get_available_providers()) > 0

# ================== 1PLAT HELPERS ==================

def generate_1plat_sign(shop_id: str, secret: str, amount: int, merchant_order_id: str) -> str:
    sign_string = f"{shop_id}:{secret}:{amount}:{merchant_order_id}"
    return hashlib.md5(sign_string.encode()).hexdigest()

def verify_1plat_signature(body: dict, shop_secret: str) -> bool:
    received_sign = body.get('signature', '')
    received_sign_v2 = body.get('signature_v2', '')
    
    merchant_id = str(body.get('merchant_id', ''))
    amount = str(body.get('amount', ''))
    shop_id = str(ONEPLATPAY_SHOP_ID)
    
    calculated_v2 = hashlib.md5(f"{merchant_id}{amount}{shop_id}{shop_secret}".encode()).hexdigest()
    
    if received_sign_v2 and received_sign_v2 == calculated_v2:
        return True
    
    if received_sign:
        import hmac
        payload = {k: v for k, v in body.items() if k not in ['signature', 'signature_v2']}
        payload_json = json.dumps(payload, separators=(',', ':'))
        calculated_v1 = hmac.new(shop_secret.encode(), payload_json.encode(), hashlib.sha256).hexdigest()
        if received_sign == calculated_v1:
            return True
    
    return False

@api_router.get("/payment/status")
async def payment_system_status():
    providers = get_available_providers()
    return {
        "success": True,
        "configured": len(providers) > 0,
        "providers": providers,
        "message": "Платёжные системы готовы" if providers else "Платёжные системы не настроены"
    }

@api_router.get("/payment/providers")
async def get_payment_providers():
    """Get list of available payment providers"""
    return {"success": True, "providers": get_available_providers()}

@api_router.post("/payment/create")
async def create_payment(request: Request, user: dict = Depends(get_current_user), _=rate_limit("payment")):
    data = await request.json()
    
    if user.get("is_demo"):
        raise HTTPException(status_code=403, detail="Пополнение недоступно в демо-режиме. Авторизуйтесь через Telegram.")
    
    providers = get_available_providers()
    if not providers:
        raise HTTPException(status_code=503, detail="Платёжные системы не настроены")
    
    amount = int(data.get("amount", 100))
    provider = data.get("provider", "1plat")
    method = data.get("method", "auto")
    
    # If method is 'auto', use the first available method for the provider
    if method == "auto":
        provider_obj = next((p for p in providers if p["id"] == provider), None)
        if provider_obj and provider_obj.get("methods"):
            method = provider_obj["methods"][0]
        else:
            method = "sbp"  # Default fallback
    
    promo_code = data.get("promo_code", "").strip()
    
    min_deposit = int(os.environ.get('MIN_DEPOSIT', 150))
    if amount < min_deposit:
        raise HTTPException(status_code=400, detail=f"Минимальная сумма: {min_deposit}₽")
    
    # Check promo code for deposit bonus
    promo_bonus = 0
    if promo_code:
        promo = await db.promos.find_one({"name": promo_code, "status": False}, {"_id": 0})
        if promo and promo.get("type") == "deposit":
            promo_bonus = promo.get("bonus_percent", 0)
    
    payment_id = str(uuid.uuid4())
    payment = {
        "id": payment_id,
        "user_id": user["id"],
        "amount": amount,
        "provider": provider,
        "method": method,
        "promo_code": promo_code,
        "promo_bonus": promo_bonus,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payments.insert_one(payment)
    
    try:
        result = None
        
        if provider == "admin":
            # Admin deposit - just create pending payment and return contact info
            result = {
                "success": True,
                "url": None,
                "external_id": payment_id,
                "is_admin_deposit": True,
                "contact": "@easymoneysupportvip",
                "instructions": f"Для пополнения на сумму {amount}₽ свяжитесь с администратором"
            }
        elif provider == "nicepay":
            result = await create_nicepay_payment(payment_id, user, amount, method)
        elif provider == "1plat":
            result = await create_1plat_payment(payment_id, user, amount, method)
        elif provider == "p2paradise":
            result = await create_p2paradise_payment(payment_id, user, amount, method)
        elif provider == "cryptobot":
            result = await create_cryptobot_payment(payment_id, user, amount, method)
        elif provider == "cryptocloud":
            result = await create_cryptocloud_payment(payment_id, user, amount, method)
        else:
            raise HTTPException(status_code=400, detail="Неизвестный провайдер")
        
        if result and result.get("success"):
            update_data = {
                "external_id": result.get("external_id")
            }
            
            # Only set payment_url if it exists (not for admin deposits)
            if result.get("url"):
                update_data["payment_url"] = result.get("url")
            
            await db.payments.update_one(
                {"id": payment_id},
                {"$set": update_data}
            )
            
            # Return different response for admin deposits
            if result.get("is_admin_deposit"):
                return {
                    "success": True,
                    "payment_id": payment_id,
                    "is_admin_deposit": True,
                    "contact": result.get("contact"),
                    "instructions": result.get("instructions"),
                    "message": "Свяжитесь с администратором для пополнения"
                }
            
            return {
                "success": True,
                "payment_id": payment_id,
                "payment_url": result.get("url"),
                "message": "Перенаправление на оплату..."
            }
        else:
            error = result.get("error", "Ошибка создания платежа") if result else "Ошибка"
            await db.payments.delete_one({"id": payment_id})
            raise HTTPException(status_code=400, detail=error)
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Payment error: {e}")
        await db.payments.delete_one({"id": payment_id})
        raise HTTPException(status_code=500, detail="Внутренняя ошибка")

# ================== NICEPAY PAYMENT ==================

def generate_nicepay_hash(params: dict, secret: str) -> str:
    """Generate NicePay signature hash"""
    # Sort params alphabetically, exclude hash
    sorted_params = sorted([(k, v) for k, v in params.items() if k != 'hash'], key=lambda x: x[0])
    # Join values with {np} separator
    values = [str(v) for k, v in sorted_params]
    values.append(secret)
    hash_string = '{np}'.join(values)
    return hashlib.sha256(hash_string.encode()).hexdigest()

def verify_nicepay_hash(params: dict, secret: str) -> bool:
    """Verify NicePay callback hash"""
    received_hash = params.get('hash', '')
    params_copy = {k: v for k, v in params.items() if k != 'hash'}
    calculated_hash = generate_nicepay_hash(params_copy, secret)
    return received_hash == calculated_hash

async def create_nicepay_payment(payment_id: str, user: dict, amount: int, method: str) -> dict:
    """Create payment via NicePay API"""
    try:
        base_url = os.environ.get('SITE_URL', 'https://easymoney33.pro')
        
        # NicePay expects amount in kopeks (cents)
        amount_kopeks = amount * 100
        
        # Create payment data according to NicePay API
        payment_data = {
            "merchant_id": NICEPAY_MERCHANT_ID,
            "secret": NICEPAY_SECRET,  # NicePay requires secret parameter
            "amount": str(amount_kopeks),  # Amount in kopeks as string
            "currency": "RUB",  # Currency code
            "order_id": payment_id,
            "customer": f"user_{user['id'][:8]}",  # Customer identifier
            "description": f"Пополнение баланса {amount}₽",
            "success_url": f"{base_url}/wallet?status=success",
            "fail_url": f"{base_url}/wallet?status=fail",
            "callback_url": f"{base_url}/api/payment/callback/nicepay"
        }
        
        # Generate signature hash
        params_for_hash = {
            "merchant_id": NICEPAY_MERCHANT_ID,
            "amount": str(amount_kopeks),
            "order_id": payment_id,
            "description": payment_data["description"]
        }
        payment_data["hash"] = generate_nicepay_hash(params_for_hash, NICEPAY_SECRET)
        
        logging.info(f"Creating NicePay payment: order_id={payment_id}, amount={amount}₽, data={payment_data}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{NICEPAY_BASE_URL}/payment",  # Changed from /payment/create to /payment
                json=payment_data,
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            logging.info(f"NicePay response status={response.status_code}: {result}")
            
            # NicePay returns different response formats
            # Check for success in multiple ways
            if response.status_code == 200:
                # Try to get payment URL from different possible fields
                payment_url = None
                external_id = None
                
                if isinstance(result, dict):
                    # Format 1: {status: "success", data: {link: "...", payment_id: "..."}}
                    if result.get("status") == "success" and result.get("data"):
                        data = result["data"]
                        payment_url = data.get("link") or data.get("url") or data.get("payment_url")
                        external_id = data.get("payment_id") or data.get("id")
                    # Format 2: {link: "...", payment_id: "..."}
                    elif result.get("link") or result.get("url"):
                        payment_url = result.get("link") or result.get("url") or result.get("payment_url")
                        external_id = result.get("payment_id") or result.get("id") or payment_id
                    # Format 3: {success: true, payment_url: "..."}
                    elif result.get("success") and (result.get("payment_url") or result.get("url")):
                        payment_url = result.get("payment_url") or result.get("url") or result.get("link")
                        external_id = result.get("payment_id") or result.get("id") or payment_id
                
                if payment_url:
                    logging.info(f"NicePay payment created successfully: url={payment_url}, external_id={external_id}")
                    return {
                        "success": True,
                        "url": payment_url,
                        "external_id": external_id or payment_id
                    }
            
            # If we got here, payment creation failed
            error_msg = "Ошибка создания платежа"
            if isinstance(result, dict):
                error_msg = result.get("message") or result.get("error") or result.get("data", {}).get("message", error_msg)
            
            logging.error(f"NicePay payment creation failed: {error_msg}")
            return {"success": False, "error": error_msg}
                
    except Exception as e:
        logging.error(f"NicePay error: {e}")
        return {"success": False, "error": str(e)}

# ================== 1PLAT PAYMENT ==================

async def create_1plat_payment(payment_id: str, user: dict, amount: int, method: str) -> dict:
    """Create payment via 1plat - method will be selected on payment page"""
    max_retries = 2
    
    # Validate amount
    if amount < 100:
        return {"success": False, "error": "Минимальная сумма 100₽"}
    if amount > 100000:
        return {"success": False, "error": "Максимальная сумма 100000₽"}
    
    for attempt in range(max_retries + 1):
        try:
            # Don't specify method - user will choose on payment page
            order_data = {
                "merchant_order_id": payment_id,
                "user_id": str(user["id"]),
                "amount": int(amount),
                "email": f"user{user['id'][:8]}@easymoney33.pro"
                # No method specified - user chooses on 1plat page
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{ONEPLATPAY_BASE_URL}/api/merchant/order/create/by-api",
                    json=order_data,
                    headers={
                        "Content-Type": "application/json",
                        "x-shop": ONEPLATPAY_SHOP_ID,
                        "x-secret": ONEPLATPAY_SECRET
                    }
                )
                
                # Handle response
                if response.status_code >= 500:
                    logging.warning(f"1plat server error (attempt {attempt + 1}): {response.status_code}")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                        continue
                    return {"success": False, "error": "Сервер платежной системы временно недоступен. Попробуйте позже."}
                
                try:
                    result = response.json()
                except:
                    logging.error(f"1plat invalid JSON response: {response.text}")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                        continue
                    return {"success": False, "error": "Ошибка платежной системы. Попробуйте другой способ."}
                
                logging.info(f"1plat response (attempt {attempt + 1}): {result}")
                
                if result.get("success") == 1 or result.get("success") == True:
                    return {
                        "success": True,
                        "url": result.get("url"),
                        "external_id": result.get("guid") or result.get("id")
                    }
                
                # Check for specific errors
                error_msg = result.get("message") or result.get("error") or "Ошибка платежной системы"
                logging.error(f"1plat error: {error_msg}")
                
                # Retry on server errors
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue
                
                return {"success": False, "error": error_msg}
                
        except httpx.TimeoutException:
            logging.error(f"1plat timeout (attempt {attempt + 1})")
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            return {"success": False, "error": "Превышено время ожидания. Попробуйте позже."}
        except Exception as e:
            logging.error(f"1plat error (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            return {"success": False, "error": "Ошибка подключения к платежной системе"}
    
    return {"success": False, "error": "Не удалось создать платеж. Попробуйте позже."}

# ================== P2PARADISE PAYMENT ==================

async def create_p2paradise_payment(payment_id: str, user: dict, amount: int, method: str) -> dict:
    """Create payment via P2Paradise API"""
    try:
        # Amount in kopeks
        amount_kopeks = amount * 100
        base_url = os.environ.get('SITE_URL', 'https://easymoney33.pro')
        
        payment_data = {
            "amount": amount_kopeks,
            "payment_method": method,  # sbp-card, sbp, card
            "merchant_customer_id": user["id"],
            "ip": "127.0.0.1",
            "description": f"Пополнение баланса #{payment_id[:8]}",
            "return_url": f"{base_url}/wallet",
            "metadata": {
                "payment_id": payment_id,
                "user_id": user["id"]
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{P2PARADISE_BASE_URL}/api/payments",
                json=payment_data,
                headers={
                    "Content-Type": "application/json",
                    "merchant-id": P2PARADISE_MERCHANT_ID,
                    "merchant-secret-key": P2PARADISE_API_KEY
                }
            )
            result = response.json()
            logging.info(f"P2Paradise response: {result}")
            
            if result.get("uuid"):
                return {
                    "success": True,
                    "url": result.get("redirect_url"),
                    "external_id": result.get("uuid")
                }
            return {"success": False, "error": result.get("message", "Ошибка P2Paradise")}
    except Exception as e:
        logging.error(f"P2Paradise error: {e}")
        return {"success": False, "error": str(e)}

# ================== CRYPTO BOT PAYMENT ==================

async def create_cryptobot_payment(payment_id: str, user: dict, amount: int, currency: str = "USDT") -> dict:
    """Create payment via Telegram Crypto Bot (@CryptoBot)
    
    Uses Crypto Pay API: https://help.crypt.bot/crypto-pay-api
    """
    try:
        base_url = os.environ.get('SITE_URL', 'https://easymoney33.pro')
        
        # Crypto Pay API endpoint
        api_url = "https://pay.crypt.bot/api"
        
        # Create invoice parameters
        invoice_params = {
            "currency_type": "fiat",
            "fiat": "RUB",
            "amount": str(amount),
            "accepted_assets": "USDT,TON,BTC,ETH,LTC,BNB,TRX,USDC",
            "description": f"Пополнение баланса EasyMoney",
            "paid_btn_name": "callback",
            "paid_btn_url": f"{base_url}/wallet?status=success",
            "payload": json.dumps({"payment_id": payment_id, "user_id": user["id"]}),
            "expires_in": 3600,
            "allow_comments": False,
            "allow_anonymous": True
        }
        
        logging.info(f"Creating CryptoBot invoice: amount={amount}₽")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/createInvoice",
                data=invoice_params,
                headers={
                    "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
                }
            )
            result = response.json()
            logging.info(f"CryptoBot response: {result}")
            
            if result.get("ok") and result.get("result"):
                invoice = result["result"]
                # bot_invoice_url - URL для оплаты через Telegram
                # mini_app_invoice_url - URL для оплаты через Mini App
                # pay_url - прямая ссылка на оплату
                pay_url = invoice.get("bot_invoice_url") or invoice.get("mini_app_invoice_url") or invoice.get("pay_url")
                return {
                    "success": True,
                    "url": pay_url,
                    "external_id": str(invoice.get("invoice_id"))
                }
            
            error_msg = result.get("error", {}).get("name", "Ошибка CryptoBot")
            if isinstance(result.get("error"), str):
                error_msg = result.get("error")
            return {"success": False, "error": error_msg}
    except Exception as e:
        logging.error(f"CryptoBot error: {e}")
        return {"success": False, "error": str(e)}

# ================== CRYPTOCLOUD PAYMENT ==================

async def create_cryptocloud_payment(payment_id: str, user: dict, amount: int, currency: str = "USDT") -> dict:
    """Create payment via CryptoCloud"""
    try:
        base_url = os.environ.get('SITE_URL', 'https://easymoney33.pro')
        
        # CryptoCloud v2 API
        invoice_data = {
            "amount": amount,
            "shop_id": CRYPTOCLOUD_SHOP_ID,  # Shop ID from JWT token (decoded)
            "currency": "RUB",
            "order_id": payment_id
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CRYPTOCLOUD_BASE_URL}/invoice/create",
                json=invoice_data,
                headers={
                    "Authorization": f"Token {CRYPTOCLOUD_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            result = response.json()
            logging.info(f"CryptoCloud response: {result}")
            
            if result.get("status") == "success" and result.get("result"):
                invoice = result["result"]
                return {
                    "success": True,
                    "url": invoice.get("link"),
                    "external_id": invoice.get("uuid")
                }
            return {"success": False, "error": result.get("message", "Ошибка CryptoCloud")}
    except Exception as e:
        logging.error(f"CryptoCloud error: {e}")
        return {"success": False, "error": str(e)}

# ================== CRYPTOBOT WEBHOOK SETUP ==================

@api_router.post("/admin/setup-cryptobot-webhook")
async def setup_cryptobot_webhook(request: Request, _: bool = Depends(verify_admin_token)):
    """Setup CryptoBot webhook URL via API
    
    CryptoBot needs webhook URL to send payment notifications.
    Call this endpoint once after deployment.
    """
    try:
        base_url = os.environ.get('SITE_URL', 'https://easymoney33.pro')
        webhook_url = f"{base_url}/api/payment/callback/cryptobot"
        
        if not CRYPTOBOT_TOKEN:
            return {"success": False, "error": "CRYPTOBOT_TOKEN not configured"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://pay.crypt.bot/api/setWebhook",
                data={"url": webhook_url},
                headers={
                    "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
                }
            )
            result = response.json()
            logging.info(f"CryptoBot setWebhook response: {result}")
            
            if result.get("ok"):
                return {
                    "success": True,
                    "webhook_url": webhook_url,
                    "message": "Webhook успешно установлен"
                }
            
            error_msg = result.get("error", {}).get("name", "Ошибка установки webhook")
            return {"success": False, "error": error_msg}
    except Exception as e:
        logging.error(f"CryptoBot webhook setup error: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/admin/check-cryptobot")
async def check_cryptobot_status(request: Request, _: bool = Depends(verify_admin_token)):
    """Check CryptoBot API status and webhook settings"""
    try:
        if not CRYPTOBOT_TOKEN:
            return {"success": False, "error": "CRYPTOBOT_TOKEN not configured"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get app info
            response = await client.post(
                "https://pay.crypt.bot/api/getMe",
                headers={
                    "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
                }
            )
            result = response.json()
            logging.info(f"CryptoBot getMe response: {result}")
            
            if result.get("ok"):
                app_info = result.get("result", {})
                return {
                    "success": True,
                    "app_id": app_info.get("app_id"),
                    "name": app_info.get("name"),
                    "payment_processing_bot_username": app_info.get("payment_processing_bot_username")
                }
            
            error_msg = result.get("error", {}).get("name", "Ошибка API")
            return {"success": False, "error": error_msg}
    except Exception as e:
        logging.error(f"CryptoBot check error: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/payment/callback/1plat")
async def oneplatpay_callback(request: Request):
    """Callback from 1plat payment system
    
    Callback format from 1plat:
    {
        signature: 'asdw12asdv212sd',
        signature_v2: 'asfage3greawfa',
        payment_id: '123',
        guid: 'guid',
        merchant_id: '543',
        user_id: '1111',
        status: 0,  # -2 to 2 (see statuses)
        amount: 100,
        amount_to_pay: 100,
        amount_to_shop: 85,
        expired: 'date',
    }
    
    Statuses:
    -2: No payment requisites
    -1: Draft (waiting for method selection)
    0: Pending payment
    1: Successfully paid (need to confirm)
    2: Confirmed and closed
    """
    try:
        body = await request.body()
        logging.info(f"1plat callback received: {body.decode()}")
        
        data = await request.json()
        original_data = data.copy()
        
        # Verify signature (optional but recommended)
        if ONEPLATPAY_SECRET and data.get('signature_v2'):
            if not verify_1plat_signature(data, ONEPLATPAY_SECRET):
                logging.warning(f"Invalid signature in callback")
                # Continue anyway, some callbacks may have different signature format
        
        # Get payment info
        merchant_id = data.get("merchant_id") or data.get("order_id")
        guid = data.get("guid")
        status = data.get("status")  # Integer status: 0, 1, 2, -1, -2
        amount = float(data.get("amount", 0))
        amount_to_shop = float(data.get("amount_to_shop", amount))
        
        logging.info(f"Processing callback: merchant_id={merchant_id}, guid={guid}, status={status}, amount={amount}")
        
        # Find payment in DB
        payment = await db.payments.find_one({"id": merchant_id}, {"_id": 0})
        if not payment:
            payment = await db.payments.find_one({"oneplatpay_guid": guid}, {"_id": 0})
        
        if not payment:
            logging.error(f"Payment not found: merchant_id={merchant_id}, guid={guid}")
            return Response(status_code=200)  # Return 200 to stop retries
        
        # Skip if already completed or processing - prevent double credit
        if payment["status"] in ["completed", "processing"]:
            logging.info(f"Payment {merchant_id} already {payment['status']}, skipping")
            return Response(status_code=200)
        
        # Process based on status
        # Status 1 = paid (need confirmation), Status 2 = confirmed
        if status in [1, 2]:
            # Mark as processing immediately to prevent race conditions
            result = await db.payments.update_one(
                {"id": payment["id"], "status": "pending"},
                {"$set": {"status": "processing"}}
            )
            if result.modified_count == 0:
                logging.info(f"1plat: Payment {payment['id']} already being processed, skipping")
                return Response(status_code=200)
            
            # Payment successful
            user = await db.users.find_one({"id": payment["user_id"]}, {"_id": 0})
            if not user:
                logging.error(f"User not found for payment: {merchant_id}")
                await db.payments.update_one({"id": payment["id"]}, {"$set": {"status": "failed", "error": "User not found"}})
                return Response(status_code=200)
            
            # Use original amount if callback amount is different
            final_amount = amount if amount > 0 else payment.get("amount", 0)
            
            # Calculate bonus from promo code
            bonus = 0
            wager = 0  # Wager only for bonus, not for deposit!
            if payment.get("promo_code"):
                promo = await db.promos.find_one({"name": payment["promo_code"], "status": False}, {"_id": 0})
                if promo and promo.get("limited", 0) < promo.get("limit", 0):
                    if promo.get("type") == 1:
                        bonus = final_amount * (promo.get("bonus_percent", 0) / 100)
                    else:
                        bonus = promo.get("reward", 0)
                    # FIXED: Wager только на бонус, не на депозит!
                    wager_mult = promo.get("wager_multiplier", 3)
                    wager = bonus * wager_mult
                    await db.promos.update_one({"id": promo["id"]}, {"$inc": {"limited": 1}})
                    logging.info(f"1plat: Promo applied! bonus={bonus}₽, wager={wager}₽ (x{wager_mult} on bonus)")
            
            total_amount = final_amount + bonus
            
            # Update user balance - deposit goes to deposit_balance, bonus to promo_balance
            await db.users.update_one(
                {"id": user["id"]},
                {"$inc": {
                    "balance": total_amount,  # Old field for compatibility
                    "deposit_balance": final_amount,  # Deposit only
                    "promo_balance": bonus,  # Promo bonus only
                    "deposit": final_amount,
                    "wager": wager,
                    "total_deposited": final_amount
                }}
            )
            
            # Calculate cashback from deposit (not from bets!)
            cashback = await calculate_deposit_cashback(user["id"], final_amount)
            
            # Update payment status
            await db.payments.update_one(
                {"id": payment["id"]},
                {"$set": {
                    "status": "completed", 
                    "bonus": bonus, 
                    "cashback": cashback,
                    "actual_amount": final_amount,
                    "amount_to_shop": amount_to_shop,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "callback_data": original_data
                }}
            )
            
            # Add referral bonus
            await add_ref_bonus(user["id"], final_amount)
            
            logging.info(f"Payment {merchant_id} completed. User {user['id']} balance updated by {total_amount}, cashback={cashback}₽")
            
            # Return 200 or 201 to confirm receipt
            return Response(status_code=200)
        
        elif status in [-1, -2, -3]:
            # Payment failed or cancelled
            await db.payments.update_one(
                {"id": payment["id"]},
                {"$set": {"status": "failed", "callback_data": original_data}}
            )
            logging.info(f"Payment {merchant_id} marked as failed (status={status})")
            return Response(status_code=200)
        
        else:
            # Status 0 = pending
            logging.info(f"Payment {merchant_id} still pending (status={status})")
            return Response(status_code=200)
    
    except Exception as e:
        logging.error(f"1plat callback error: {e}", exc_info=True)
        return Response(status_code=200)  # Return 200 to prevent retries

# ================== CRYPTOBOT WEBHOOK ==================

@api_router.post("/payment/callback/cryptobot")
async def cryptobot_callback(request: Request):
    """Webhook callback from Crypto Bot (@CryptoBot)
    
    Crypto Bot sends webhook when invoice is paid.
    Payload contains invoice_id and status.
    """
    try:
        body = await request.body()
        logging.info(f"CryptoBot callback received: {body.decode()}")
        
        data = await request.json()
        
        # CryptoBot sends update_type and payload
        update_type = data.get("update_type")
        payload = data.get("payload", {})
        
        if update_type != "invoice_paid":
            logging.info(f"CryptoBot: ignoring update_type={update_type}")
            return Response(status_code=200)
        
        # Get invoice info from payload
        invoice_id = str(payload.get("invoice_id", ""))
        status = payload.get("status", "")
        paid_amount = float(payload.get("paid_amount", 0))
        paid_asset = payload.get("paid_asset", "")
        paid_fiat_rate = float(payload.get("paid_fiat_rate", 0))
        
        # Get our payment_id from payload field
        custom_payload = payload.get("payload", "{}")
        try:
            custom_data = json.loads(custom_payload) if isinstance(custom_payload, str) else custom_payload
            payment_id = custom_data.get("payment_id")
            user_id = custom_data.get("user_id")
        except:
            payment_id = None
            user_id = None
        
        logging.info(f"CryptoBot processing: invoice_id={invoice_id}, status={status}, payment_id={payment_id}")
        
        # Find payment by external_id or payment_id
        payment = None
        if payment_id:
            payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
        if not payment and invoice_id:
            payment = await db.payments.find_one({"external_id": invoice_id}, {"_id": 0})
        
        if not payment:
            logging.error(f"CryptoBot: Payment not found: invoice_id={invoice_id}, payment_id={payment_id}")
            return Response(status_code=200)
        
        # Skip if already completed - IMPORTANT: prevent double credit
        if payment["status"] == "completed":
            logging.info(f"CryptoBot: Payment {payment['id']} already completed, skipping")
            return Response(status_code=200)
        
        # Mark payment as processing immediately to prevent race conditions
        result = await db.payments.update_one(
            {"id": payment["id"], "status": "pending"},
            {"$set": {"status": "processing"}}
        )
        if result.modified_count == 0:
            logging.info(f"CryptoBot: Payment {payment['id']} already being processed, skipping")
            return Response(status_code=200)
        
        # Payment successful
        if status == "paid":
            user = await db.users.find_one({"id": payment["user_id"]}, {"_id": 0})
            if not user:
                logging.error(f"CryptoBot: User not found for payment: {payment['id']}")
                await db.payments.update_one({"id": payment["id"]}, {"$set": {"status": "failed", "error": "User not found"}})
                return Response(status_code=200)
            
            # Use original RUB amount from payment record (NOT from callback)
            final_amount = payment.get("amount", 0)
            
            logging.info(f"CryptoBot: Processing payment {payment['id']} for {final_amount}₽ to user {user['id']}")
            
            # Calculate bonus from promo code
            bonus = 0
            wager = 0  # Wager only for bonus, not for deposit!
            if payment.get("promo_code"):
                promo = await db.promos.find_one({"name": payment["promo_code"], "status": False}, {"_id": 0})
                if promo and promo.get("limited", 0) < promo.get("limit", 0):
                    if promo.get("type") == 1:
                        bonus = final_amount * (promo.get("bonus_percent", 0) / 100)
                    else:
                        bonus = promo.get("reward", 0)
                    # FIXED: Wager только на бонус!
                    wager_mult = promo.get("wager_multiplier", 3)
                    wager = bonus * wager_mult
                    await db.promos.update_one({"id": promo["id"]}, {"$inc": {"limited": 1}})
                    logging.info(f"CryptoBot: Promo applied! bonus={bonus}₽, wager={wager}₽ (x{wager_mult} on bonus)")
            
            total_amount = final_amount + bonus
            
            # Update user balance and track total deposits
            # Update user balance - deposit goes to deposit_balance, bonus to promo_balance
            await db.users.update_one(
                {"id": user["id"]},
                {"$inc": {
                    "balance": total_amount,
                    "deposit_balance": final_amount,
                    "promo_balance": bonus,
                    "deposit": final_amount,
                    "wager": wager,
                    "total_deposited": final_amount
                }}
            )
            
            # Calculate cashback from deposit (not from bets!)
            cashback = await calculate_deposit_cashback(user["id"], final_amount)
            
            # Update payment status
            await db.payments.update_one(
                {"id": payment["id"]},
                {"$set": {
                    "status": "completed",
                    "bonus": bonus,
                    "cashback": cashback,
                    "actual_amount": final_amount,
                    "paid_crypto_amount": paid_amount,
                    "paid_crypto_asset": paid_asset,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "callback_data": data
                }}
            )
            
            # Add referral bonus
            await add_ref_bonus(user["id"], final_amount)
            
            logging.info(f"CryptoBot: Payment {payment['id']} completed. User {user['id']} balance updated by {total_amount}, cashback={cashback}₽")
        
        return Response(status_code=200)
    
    except Exception as e:
        logging.error(f"CryptoBot callback error: {e}", exc_info=True)
        return Response(status_code=200)

# ================== CRYPTOCLOUD WEBHOOK ==================

@api_router.post("/payment/callback/cryptocloud")
async def cryptocloud_callback(request: Request):
    """Webhook callback from CryptoCloud
    
    CryptoCloud sends webhook when invoice status changes.
    """
    try:
        body = await request.body()
        logging.info(f"CryptoCloud callback received: {body.decode()}")
        
        data = await request.json()
        
        # CryptoCloud callback format
        status = data.get("status")
        order_id = data.get("order_id")  # This is our payment_id
        invoice_id = data.get("invoice_id")
        amount_crypto = data.get("amount_crypto")
        currency = data.get("currency")
        
        logging.info(f"CryptoCloud processing: order_id={order_id}, status={status}, invoice_id={invoice_id}")
        
        # Find payment
        payment = None
        if order_id:
            payment = await db.payments.find_one({"id": order_id}, {"_id": 0})
        if not payment and invoice_id:
            payment = await db.payments.find_one({"external_id": invoice_id}, {"_id": 0})
        
        if not payment:
            logging.error(f"CryptoCloud: Payment not found: order_id={order_id}, invoice_id={invoice_id}")
            return Response(status_code=200)
        
        # Skip if already completed or processing - prevent double credit
        if payment["status"] in ["completed", "processing"]:
            logging.info(f"CryptoCloud: Payment {payment['id']} already {payment['status']}, skipping")
            return Response(status_code=200)
        
        # Mark as processing immediately
        result = await db.payments.update_one(
            {"id": payment["id"], "status": "pending"},
            {"$set": {"status": "processing"}}
        )
        if result.modified_count == 0:
            logging.info(f"CryptoCloud: Payment {payment['id']} already being processed, skipping")
            return Response(status_code=200)
        
        # Payment successful
        if status == "success":
            user = await db.users.find_one({"id": payment["user_id"]}, {"_id": 0})
            if not user:
                logging.error(f"CryptoCloud: User not found for payment: {payment['id']}")
                await db.payments.update_one({"id": payment["id"]}, {"$set": {"status": "failed", "error": "User not found"}})
                return Response(status_code=200)
            
            # Use original RUB amount from payment
            final_amount = payment.get("amount", 0)
            
            logging.info(f"CryptoCloud: Processing payment {payment['id']} for {final_amount}₽ to user {user['id']}")
            
            # Calculate bonus from promo code
            bonus = 0
            wager = 0  # Wager only for bonus!
            if payment.get("promo_code"):
                promo = await db.promos.find_one({"name": payment["promo_code"], "status": False}, {"_id": 0})
                if promo and promo.get("limited", 0) < promo.get("limit", 0):
                    if promo.get("type") == 1:
                        bonus = final_amount * (promo.get("bonus_percent", 0) / 100)
                    else:
                        bonus = promo.get("reward", 0)
                    # FIXED: Wager только на бонус!
                    wager_mult = promo.get("wager_multiplier", 3)
                    wager = bonus * wager_mult
                    await db.promos.update_one({"id": promo["id"]}, {"$inc": {"limited": 1}})
                    logging.info(f"CryptoCloud: Promo applied! bonus={bonus}₽, wager={wager}₽ (x{wager_mult} on bonus)")
            
            total_amount = final_amount + bonus
            
            # Update user balance and track total deposits
            # Update user balance - deposit goes to deposit_balance, bonus to promo_balance
            await db.users.update_one(
                {"id": user["id"]},
                {"$inc": {
                    "balance": total_amount,
                    "deposit_balance": final_amount,
                    "promo_balance": bonus,
                    "deposit": final_amount,
                    "wager": wager,
                    "total_deposited": final_amount
                }}
            )
            
            # Calculate cashback from deposit (not from bets!)
            cashback = await calculate_deposit_cashback(user["id"], final_amount)
            
            # Update payment status
            await db.payments.update_one(
                {"id": payment["id"]},
                {"$set": {
                    "status": "completed",
                    "bonus": bonus,
                    "cashback": cashback,
                    "actual_amount": final_amount,
                    "paid_crypto_amount": amount_crypto,
                    "paid_crypto_currency": currency,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "callback_data": data
                }}
            )
            
            # Add referral bonus
            await add_ref_bonus(user["id"], final_amount)
            
            logging.info(f"CryptoCloud: Payment {payment['id']} completed. User {user['id']} balance updated by {total_amount}, cashback={cashback}₽")
        
        elif status in ["cancel", "fail"]:
            await db.payments.update_one(
                {"id": payment["id"]},
                {"$set": {"status": "failed", "callback_data": data}}
            )
            logging.info(f"CryptoCloud: Payment {payment['id']} marked as failed")
        
        return Response(status_code=200)
    
    except Exception as e:
        logging.error(f"CryptoCloud callback error: {e}", exc_info=True)
        return Response(status_code=200)

# ================== NICEPAY WEBHOOK ==================

@api_router.get("/payment/callback/nicepay")
async def nicepay_callback(request: Request):
    """Webhook callback from NicePay (GET request with query params)
    
    NicePay sends GET request with these params:
    - result: success/error
    - payment_id: NicePay payment ID
    - merchant_id: our merchant ID
    - order_id: our payment_id
    - amount: amount in kopeks
    - amount_currency: RUB
    - profit: our profit in kopeks
    - profit_currency: USDT
    - method: payment method
    - hash: signature
    """
    try:
        params = dict(request.query_params)
        logging.info(f"NicePay callback received: {params}")
        
        # Verify hash
        if NICEPAY_SECRET and params.get('hash'):
            if not verify_nicepay_hash(params, NICEPAY_SECRET):
                logging.warning(f"NicePay: Invalid hash in callback")
                # Continue anyway for debugging
        
        result = params.get("result")
        order_id = params.get("order_id")  # Our payment_id
        nicepay_payment_id = params.get("payment_id")
        amount_kopeks = int(params.get("amount", 0))
        amount = amount_kopeks / 100  # Convert to rubles
        
        logging.info(f"NicePay processing: order_id={order_id}, result={result}, amount={amount}₽")
        
        # Find payment
        payment = None
        if order_id:
            payment = await db.payments.find_one({"id": order_id}, {"_id": 0})
        if not payment and nicepay_payment_id:
            payment = await db.payments.find_one({"external_id": nicepay_payment_id}, {"_id": 0})
        
        if not payment:
            logging.error(f"NicePay: Payment not found: order_id={order_id}")
            return Response(content=json.dumps({"result": {"message": "Payment not found"}}), media_type="application/json")
        
        # Skip if already completed or processing - prevent double credit
        if payment["status"] in ["completed", "processing"]:
            logging.info(f"NicePay: Payment {payment['id']} already {payment['status']}, skipping")
            return Response(content=json.dumps({"result": {"message": "Already processed"}}), media_type="application/json")
        
        if result == "success":
            # Mark as processing immediately to prevent race conditions
            update_result = await db.payments.update_one(
                {"id": payment["id"], "status": "pending"},
                {"$set": {"status": "processing"}}
            )
            if update_result.modified_count == 0:
                logging.info(f"NicePay: Payment {payment['id']} already being processed, skipping")
                return Response(content=json.dumps({"result": {"message": "Already processing"}}), media_type="application/json")
            
            # Payment successful
            user = await db.users.find_one({"id": payment["user_id"]}, {"_id": 0})
            if not user:
                logging.error(f"NicePay: User not found for payment: {payment['id']}")
                await db.payments.update_one({"id": payment["id"]}, {"$set": {"status": "failed", "error": "User not found"}})
                return Response(content=json.dumps({"error": {"message": "User not found"}}), media_type="application/json")
            
            # Use original amount or callback amount
            final_amount = amount if amount > 0 else payment.get("amount", 0)
            
            # Calculate bonus from promo code
            bonus = 0
            wager = 0  # Wager only for bonus!
            if payment.get("promo_code"):
                promo = await db.promos.find_one({"name": payment["promo_code"], "status": False}, {"_id": 0})
                if promo and promo.get("limited", 0) < promo.get("limit", 0):
                    if promo.get("type") == 1:
                        bonus = final_amount * (promo.get("bonus_percent", 0) / 100)
                    else:
                        bonus = promo.get("reward", 0)
                    # FIXED: Wager только на бонус!
                    wager_mult = promo.get("wager_multiplier", 3)
                    wager = bonus * wager_mult
                    await db.promos.update_one({"id": promo["id"]}, {"$inc": {"limited": 1}})
                    logging.info(f"NicePay: Promo applied! bonus={bonus}₽, wager={wager}₽ (x{wager_mult} on bonus)")
            
            total_amount = final_amount + bonus
            
            # Update user balance and track total deposits
            # Update user balance - deposit goes to deposit_balance, bonus to promo_balance
            await db.users.update_one(
                {"id": user["id"]},
                {"$inc": {
                    "balance": total_amount,
                    "deposit_balance": final_amount,
                    "promo_balance": bonus,
                    "deposit": final_amount,
                    "wager": wager,
                    "total_deposited": final_amount
                }}
            )
            
            # Update payment status
            await db.payments.update_one(
                {"id": payment["id"]},
                {"$set": {
                    "status": "completed",
                    "bonus": bonus,
                    "actual_amount": final_amount,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "callback_data": params
                }}
            )
            
            # Add referral bonus
            await add_ref_bonus(user["id"], final_amount)
            
            # Calculate and add cashback
            cashback = await calculate_deposit_cashback(user["id"], final_amount)
            
            logging.info(f"NicePay: Payment {payment['id']} completed. User {user['id']} balance updated by {total_amount}₽ (cashback: {cashback}₽)")
            return Response(content=json.dumps({"result": {"message": "Success"}}), media_type="application/json")
        
        elif result == "error":
            await db.payments.update_one(
                {"id": payment["id"]},
                {"$set": {"status": "failed", "callback_data": params}}
            )
            logging.info(f"NicePay: Payment {payment['id']} marked as failed")
            return Response(content=json.dumps({"error": {"message": "Payment failed"}}), media_type="application/json")
        
        return Response(content=json.dumps({"result": {"message": "Processed"}}), media_type="application/json")
    
    except Exception as e:
        logging.error(f"NicePay callback error: {e}", exc_info=True)
        return Response(content=json.dumps({"error": {"message": str(e)}}), media_type="application/json")

@api_router.get("/payout/callback/nicepay")
async def nicepay_payout_callback(request: Request):
    """Webhook callback from NicePay for payouts (GET request with query params)
    
    NicePay sends GET request with these params:
    - result: success_payout/error_payout
    - payout_id: NicePay payout ID
    - merchant_id: our merchant ID
    - order_id: our withdraw_id
    - amount: amount in kopeks
    - amount_currency: currency
    - method: payout method
    - hash: signature
    """
    try:
        params = dict(request.query_params)
        logging.info(f"NicePay payout callback received: {params}")
        
        # Verify hash
        if NICEPAY_SECRET and params.get('hash'):
            if not verify_nicepay_hash(params, NICEPAY_SECRET):
                logging.warning(f"NicePay payout: Invalid hash in callback")
        
        result = params.get("result")
        order_id = params.get("order_id")  # Our withdraw_id
        nicepay_payout_id = params.get("payout_id")
        
        logging.info(f"NicePay payout processing: order_id={order_id}, result={result}")
        
        # Find withdrawal
        withdraw = None
        if order_id:
            withdraw = await db.withdraws.find_one({"id": order_id}, {"_id": 0})
        if not withdraw and nicepay_payout_id:
            withdraw = await db.withdraws.find_one({"external_id": nicepay_payout_id}, {"_id": 0})
        
        if not withdraw:
            logging.error(f"NicePay payout: Withdrawal not found: order_id={order_id}")
            return Response(content=json.dumps({"error": {"message": "Withdrawal not found"}}), media_type="application/json")
        
        # Skip if already completed
        if withdraw["status"] == "completed":
            logging.info(f"NicePay payout: Withdrawal {withdraw['id']} already completed")
            return Response(content=json.dumps({"result": {"message": "Already completed"}}), media_type="application/json")
        
        if result == "success_payout":
            # Payout successful
            await db.withdraws.update_one(
                {"id": withdraw["id"]},
                {"$set": {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "callback_data": params
                }}
            )
            logging.info(f"NicePay payout: Withdrawal {withdraw['id']} completed successfully")
            return Response(content=json.dumps({"result": {"message": "Success"}}), media_type="application/json")
        
        elif result == "error_payout":
            # Payout failed - refund balance
            reason = params.get("reason", "Unknown error")
            await db.withdraws.update_one(
                {"id": withdraw["id"]},
                {"$set": {"status": "failed", "error_reason": reason, "callback_data": params}}
            )
            
            # Refund balance to user
            await db.users.update_one(
                {"id": withdraw["user_id"]},
                {"$inc": {"balance": withdraw["amount"]}}
            )
            
            logging.info(f"NicePay payout: Withdrawal {withdraw['id']} failed, balance refunded")
            return Response(content=json.dumps({"error": {"message": "Payout failed, refunded"}}), media_type="application/json")
        
        return Response(content=json.dumps({"result": {"message": "Processed"}}), media_type="application/json")
    
    except Exception as e:
        logging.error(f"NicePay payout callback error: {e}", exc_info=True)
        return Response(content=json.dumps({"error": {"message": str(e)}}), media_type="application/json")

@api_router.post("/payment/mock/complete/{payment_id}")
async def complete_mock_payment(payment_id: str):
    """Mock payment completion for testing - includes double-payment protection"""
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Платеж не найден")
    
    # Protection against double payments - use atomic update
    if payment["status"] != "pending":
        raise HTTPException(status_code=400, detail="Платеж уже обработан")
    
    # Mark as processing immediately (atomic operation)
    result = await db.payments.update_one(
        {"id": payment_id, "status": "pending"},
        {"$set": {"status": "processing"}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Платеж уже обрабатывается")
    
    user = await db.users.find_one({"id": payment["user_id"]}, {"_id": 0})
    if not user:
        await db.payments.update_one({"id": payment_id}, {"$set": {"status": "failed", "error": "User not found"}})
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    bonus = 0
    wager = 0  # Wager only for bonus, not for deposit!
    if payment.get("promo_code"):
        promo = await db.promos.find_one({"name": payment["promo_code"], "status": False}, {"_id": 0})
        if promo and promo.get("limited", 0) < promo.get("limit", 0):
            if promo.get("type") == 1:
                # Type 1: Percentage bonus
                bonus = payment["amount"] * (promo.get("bonus_percent", 0) / 100)
            else:
                # Type 0: Fixed bonus
                bonus = promo.get("reward", 0)
            # IMPORTANT: Wager applies only to bonus, not to deposit!
            wager_mult = promo.get("wager_multiplier", 3)
            wager = bonus * wager_mult
            await db.promos.update_one({"id": promo["id"]}, {"$inc": {"limited": 1}})
            logging.info(f"Mock: Promo applied! bonus={bonus}₽, wager={wager}₽ (x{wager_mult} on bonus only)")
    
    total_amount = payment["amount"] + bonus
    
    # Update user balance - deposit to deposit_balance, bonus to promo_balance
    await db.users.update_one(
        {"id": user["id"]}, 
        {"$inc": {
            "balance": total_amount,
            "deposit_balance": payment["amount"],  # Deposit only
            "promo_balance": bonus,  # Promo bonus only
            "deposit": payment["amount"],
            "wager": wager,  # Wager from bonus only!
            "total_deposited": payment["amount"]
        }}
    )
    
    # Mark as completed with all details
    await db.payments.update_one(
        {"id": payment_id}, 
        {"$set": {
            "status": "completed", 
            "bonus": bonus,
            "wager": wager,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Add referral bonus to inviter
    await add_ref_bonus(user["id"], payment["amount"])
    
    logging.info(f"Mock payment {payment_id} completed: amount={payment['amount']}₽, bonus={bonus}₽, wager={wager}₽")
    
    return {"success": True, "amount": total_amount, "bonus": bonus, "wager": wager}

@api_router.get("/payment/history")
async def payment_history(user: dict = Depends(get_current_user)):
    payments = await db.payments.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    return {"success": True, "payments": payments}

# ================== WITHDRAWALS ==================

async def process_nicepay_withdrawal(withdraw_id: str, amount: float, wallet: str, system: str) -> dict:
    """Process withdrawal through NicePay API"""
    if not NICEPAY_MERCHANT_ID or not NICEPAY_SECRET:
        return {"success": False, "error": "NicePay не настроен"}
    
    try:
        # Map system to NicePay method
        # For SBP: phone number (79814005040)
        # For card: card number (2200100020004455)
        method_map = {
            "card": "bankcard_rub",
            "sbp": "sbp_rub",
            "yoomoney": "yoomoney_rub",
        }
        nicepay_method = method_map.get(system, "bankcard_rub")
        
        # Amount in kopeks
        amount_kopeks = int(amount * 100)
        
        payout_data = {
            "merchant_id": NICEPAY_MERCHANT_ID,
            "secret": NICEPAY_SECRET,
            "order_id": withdraw_id,
            "balance": "USDT",  # Balance to withdraw from
            "method": nicepay_method,
            "wallet": wallet,
            "amount": amount_kopeks,
            "comment": "EasyMoney withdrawal",
            "fee_merchant": True  # Commission from merchant
        }
        
        logging.info(f"Creating NicePay withdrawal: order_id={withdraw_id}, amount={amount}₽, method={nicepay_method}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{NICEPAY_BASE_URL}/payout",
                json=payout_data,
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            logging.info(f"NicePay withdrawal response: {result}")
            
            if result.get("status") == "success" and result.get("data"):
                data = result["data"]
                return {
                    "success": True,
                    "external_id": data.get("payment_id") or data.get("payout_id"),
                    "balance": data.get("balance")
                }
            else:
                error_msg = result.get("data", {}).get("message", "Ошибка выплаты NicePay")
                return {"success": False, "error": error_msg}
                
    except Exception as e:
        logging.error(f"NicePay withdrawal error: {e}")
        return {"success": False, "error": str(e)}

async def process_1plat_withdrawal(withdraw_id: str, amount: float, wallet: str, system: str) -> dict:
    """Process withdrawal through 1plat API"""
    if not is_payment_configured():
        return {"success": False, "error": "Платёжная система не настроена"}
    
    try:
        # Determine payment method based on system
        method_map = {
            "card": "card",
            "sbp": "sbp",
            "qiwi": "qiwi",
            "yoomoney": "yoomoney",
            "crypto": "crypto"
        }
        method = method_map.get(system, "card")
        
        withdraw_data = {
            "merchant_order_id": withdraw_id,
            "amount": int(amount),
            "method": method,
            "wallet": wallet
        }
        
        logging.info(f"Creating 1plat withdrawal: {withdraw_data}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ONEPLATPAY_BASE_URL}/api/merchant/payout/create/by-api",
                json=withdraw_data,
                headers={
                    "Content-Type": "application/json",
                    "x-shop": ONEPLATPAY_SHOP_ID,
                    "x-secret": ONEPLATPAY_SECRET
                }
            )
            
            result = response.json()
            logging.info(f"1plat withdrawal response: {result}")
            
            if result.get("success") == 1:
                return {
                    "success": True,
                    "guid": result.get("guid"),
                    "status": result.get("status")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("message") or result.get("error") or "Ошибка вывода"
                }
    except Exception as e:
        logging.error(f"1plat withdrawal error: {e}")
        return {"success": False, "error": str(e)}

# ================== P2PARADISE WITHDRAWAL ==================
async def process_p2paradise_withdrawal(withdraw_id: str, amount: float, wallet: str, system: str) -> dict:
    """Process withdrawal through P2Paradise API"""
    try:
        payout_data = {
            "amount": int(amount),
            "type": "card" if system == "card" else "sbp",
            "number": wallet,
            "order_id": withdraw_id
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{P2PARADISE_BASE_URL}/api/payouts",
                json=payout_data,
                headers={
                    "Content-Type": "application/json",
                    "merchant-id": P2PARADISE_MERCHANT_ID,
                    "merchant-secret-key": P2PARADISE_API_KEY
                }
            )
            result = response.json()
            logging.info(f"P2Paradise withdrawal response: {result}")
            
            if result.get("status") == "success" or result.get("success"):
                return {"success": True, "external_id": result.get("payout_id")}
            return {"success": False, "error": result.get("message", "Ошибка P2Paradise")}
    except Exception as e:
        logging.error(f"P2Paradise withdrawal error: {e}")
        return {"success": False, "error": str(e)}

# ================== CRYPTOBOT WITHDRAWAL ==================
async def process_cryptobot_withdrawal(withdraw_id: str, amount: float, wallet: str, crypto: str) -> dict:
    """Process withdrawal through CryptoBot API"""
    try:
        # Convert RUB to crypto (approximate rate)
        crypto_rates = {
            "usdt": 90,  # 1 USDT = ~90 RUB
            "btc": 9000000,  # 1 BTC = ~9M RUB
            "eth": 350000,  # 1 ETH = ~350K RUB
            "ton": 500  # 1 TON = ~500 RUB
        }
        rate = crypto_rates.get(crypto.lower(), 90)
        crypto_amount = round(amount / rate, 6)
        
        transfer_data = {
            "user_id": int(wallet) if wallet.isdigit() else 0,
            "asset": crypto.upper(),
            "amount": str(crypto_amount),
            "spend_id": withdraw_id
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CRYPTOBOT_BASE_URL}/api/transfer",
                json=transfer_data,
                headers={
                    "Content-Type": "application/json",
                    "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
                }
            )
            result = response.json()
            logging.info(f"CryptoBot withdrawal response: {result}")
            
            if result.get("ok"):
                return {"success": True, "external_id": result.get("result", {}).get("transfer_id")}
            return {"success": False, "error": result.get("error", {}).get("name", "Ошибка CryptoBot")}
    except Exception as e:
        logging.error(f"CryptoBot withdrawal error: {e}")
        return {"success": False, "error": str(e)}

# ================== CRYPTOCLOUD WITHDRAWAL ==================
async def process_cryptocloud_withdrawal(withdraw_id: str, amount: float, wallet: str, crypto: str) -> dict:
    """Process withdrawal through CryptoCloud API"""
    try:
        # CryptoCloud payout endpoint
        payout_data = {
            "shop_id": CRYPTOCLOUD_SHOP_ID,
            "amount": amount,
            "currency": "RUB",
            "network": crypto.upper(),
            "address": wallet,
            "order_id": withdraw_id
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CRYPTOCLOUD_BASE_URL}/invoice/payout",
                json=payout_data,
                headers={
                    "Authorization": f"Token {CRYPTOCLOUD_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            result = response.json()
            logging.info(f"CryptoCloud withdrawal response: {result}")
            
            if result.get("status") == "success":
                return {"success": True, "external_id": result.get("result", {}).get("uuid")}
            return {"success": False, "error": result.get("message", "Ошибка CryptoCloud")}
    except Exception as e:
        logging.error(f"CryptoCloud withdrawal error: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/withdraw/create")
async def create_withdraw(request: Request, user: dict = Depends(get_current_user), _=rate_limit("payment")):
    data = await request.json()
    settings = await get_settings()
    min_withdraw = settings.get("min_withdraw", 150)
    amount = float(data.get("amount", 150))
    wallet = data.get("wallet", "")
    system = data.get("system", "card")  # card, sbp, crypto_usdt, crypto_btc, etc.
    provider = data.get("provider", "1plat")  # 1plat, p2paradise, cryptobot, cryptocloud
    bank_name = data.get("bank_name", "")  # Name of bank for card/sbp withdrawals
    crypto_network = data.get("crypto_network", "")  # Network for crypto withdrawals (TRC20, ERC20, etc.)
    
    # Demo users cannot withdraw
    if user.get("is_demo"):
        raise HTTPException(status_code=403, detail="Вывод недоступен в демо-режиме. Авторизуйтесь через Telegram для вывода средств.")
    
    # Check if user has deposit this month (minimum 150₽)
    has_deposit = await check_user_has_deposit_this_month(user["id"])
    if not has_deposit:
        raise HTTPException(status_code=400, detail="Для вывода необходим хотя бы один депозит за текущий месяц (минимум 150₽)")
    
    if not wallet:
        raise HTTPException(status_code=400, detail="Введите реквизиты для вывода")
    
    if amount < min_withdraw:
        raise HTTPException(status_code=400, detail=f"Минимальная сумма вывода: {min_withdraw}₽")
    
    # Get withdrawable amount with promo limit (300₽) and wager check
    withdrawable_info = await get_withdrawable_amount(user["id"])
    
    # Check if amount exceeds what's available
    if amount > withdrawable_info["total"]:
        wager_msg = f" (вейджер: {withdrawable_info['wager']:.2f}₽)" if withdrawable_info.get("wager", 0) > 0 else ""
        locked_msg = f", из промо-баланса доступно макс 300₽" if withdrawable_info["locked_promo"] > 0 else ""
        raise HTTPException(
            status_code=400, 
            detail=f"Недостаточно средств для вывода. Доступно: {withdrawable_info['total']:.2f}₽{wager_msg}{locked_msg}"
        )
    
    withdraw_id = str(uuid.uuid4())
    
    # Deduct from appropriate balances (deposit first, then promo up to 300₽)
    remaining = amount
    deducted_deposit = 0
    deducted_promo = 0
    
    if withdrawable_info["from_deposit"] > 0:
        deducted_deposit = min(remaining, withdrawable_info["from_deposit"])
        remaining -= deducted_deposit
    
    if remaining > 0 and withdrawable_info["from_promo"] > 0:
        deducted_promo = min(remaining, withdrawable_info["from_promo"])
    
    # Update balances
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {
            "deposit_balance": -deducted_deposit if deducted_deposit > 0 else 0,
            "promo_balance": -deducted_promo if deducted_promo > 0 else 0,
            "balance": -(deducted_deposit + deducted_promo)  # Also update old balance field
        }}
    )
    
    # Create withdraw record with bank/crypto details
    withdraw = {
        "id": withdraw_id, 
        "user_id": user["id"], 
        "amount": amount,
        "wallet": wallet, 
        "system": system,
        "provider": provider,
        "bank_name": bank_name,
        "crypto_network": crypto_network,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.withdraws.insert_one(withdraw)
    
    # Process through selected provider
    payout_result = None
    
    # For card/sbp withdrawals, prefer NicePay for auto-payouts
    if system in ["card", "sbp"] and NICEPAY_MERCHANT_ID and NICEPAY_SECRET:
        payout_result = await process_nicepay_withdrawal(withdraw_id, amount, wallet, system)
    elif provider == "nicepay" and NICEPAY_MERCHANT_ID:
        payout_result = await process_nicepay_withdrawal(withdraw_id, amount, wallet, system)
    elif provider == "1plat" and is_payment_configured():
        payout_result = await process_1plat_withdrawal(withdraw_id, amount, wallet, system)
    elif provider == "p2paradise" and P2PARADISE_API_KEY:
        payout_result = await process_p2paradise_withdrawal(withdraw_id, amount, wallet, system)
    elif provider == "cryptobot" and CRYPTOBOT_TOKEN:
        crypto_type = system.replace("crypto_", "") if system.startswith("crypto_") else "usdt"
        payout_result = await process_cryptobot_withdrawal(withdraw_id, amount, wallet, crypto_type)
    elif provider == "cryptocloud" and CRYPTOCLOUD_API_KEY:
        crypto_type = system.replace("crypto_", "") if system.startswith("crypto_") else "usdt"
        payout_result = await process_cryptocloud_withdrawal(withdraw_id, amount, wallet, crypto_type)
    
    if payout_result and payout_result.get("success"):
        await db.withdraws.update_one(
            {"id": withdraw_id},
            {"$set": {
                "status": "processing",
                "external_id": payout_result.get("external_id") or payout_result.get("guid")
            }}
        )
        return {
            "success": True, 
            "withdraw_id": withdraw_id,
            "message": "Заявка на вывод создана и отправлена на обработку"
        }
    elif payout_result:
        # Log the error but keep the withdrawal pending for manual processing
        logging.warning(f"Auto-withdrawal failed: {payout_result.get('error')}. Withdrawal {withdraw_id} marked for manual processing.")
        await db.withdraws.update_one(
            {"id": withdraw_id},
            {"$set": {"auto_error": payout_result.get("error")}}
        )
    
    return {"success": True, "withdraw_id": withdraw_id, "message": "Заявка на вывод создана. Ожидайте обработки."}

@api_router.get("/withdraw/history")
async def withdraw_history(user: dict = Depends(get_current_user)):
    withdraws = await db.withdraws.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    return {"success": True, "withdraws": withdraws}

@api_router.get("/withdraw/info")
async def get_withdraw_info(user: dict = Depends(get_current_user)):
    """Get withdrawal information including available amount and promo limit"""
    withdrawable = await get_withdrawable_amount(user["id"])
    balances = await get_user_balances(user["id"])
    
    return {
        "success": True,
        "withdrawable_total": withdrawable["total"],
        "from_deposit": withdrawable["from_deposit"],
        "from_promo": withdrawable["from_promo"],
        "locked_promo": withdrawable["locked_promo"],
        "promo_limit": user.get("promo_withdrawal_limit", 300),
        "balances": balances,
        "wager": withdrawable.get("wager", 0),  # Use wager from withdrawable calculation
        "has_deposit_this_month": await check_user_has_deposit_this_month(user["id"]),
        "wager_info": "Вейджер блокирует только бонусный баланс. Депозит доступен для вывода всегда." if withdrawable.get("wager", 0) > 0 else None
    }

@api_router.post("/withdraw/callback/1plat")
async def oneplatpay_withdraw_callback(request: Request):
    """Callback from 1plat for payout status updates"""
    try:
        body = await request.body()
        logging.info(f"1plat payout callback received: {body.decode()}")
        
        data = await request.json()
        
        # Get withdrawal info
        merchant_id = data.get("merchant_order_id") or data.get("order_id")
        guid = data.get("guid")
        status = data.get("status")  # 1 = success, -1 = failed
        
        logging.info(f"Processing payout callback: merchant_id={merchant_id}, guid={guid}, status={status}")
        
        # Find withdrawal in DB
        withdraw = await db.withdraws.find_one({"id": merchant_id}, {"_id": 0})
        if not withdraw:
            withdraw = await db.withdraws.find_one({"oneplatpay_guid": guid}, {"_id": 0})
        
        if not withdraw:
            logging.error(f"Withdrawal not found: merchant_id={merchant_id}, guid={guid}")
            return Response(status_code=200)
        
        if withdraw["status"] == "completed":
            logging.info(f"Withdrawal {merchant_id} already completed")
            return Response(status_code=200)
        
        if status == 1 or status == 2:
            # Payout successful
            await db.withdraws.update_one(
                {"id": withdraw["id"]},
                {"$set": {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "callback_data": data
                }}
            )
            logging.info(f"Withdrawal {merchant_id} completed successfully")
        elif status in [-1, -2]:
            # Payout failed - refund user
            await db.users.update_one(
                {"id": withdraw["user_id"]},
                {"$inc": {"balance": withdraw["amount"]}}
            )
            await db.withdraws.update_one(
                {"id": withdraw["id"]},
                {"$set": {
                    "status": "failed",
                    "callback_data": data
                }}
            )
            logging.info(f"Withdrawal {merchant_id} failed, balance refunded")
        
        return Response(status_code=200)
    except Exception as e:
        logging.error(f"1plat payout callback error: {e}", exc_info=True)
        return Response(status_code=200)

# ================== PROMO ==================

@api_router.post("/promo/activate")
async def activate_promo(request: Request, user: dict = Depends(get_current_user)):
    data = await request.json()
    code = data.get("code", "")
    
    promo = await db.promos.find_one({"name": code, "status": False}, {"_id": 0})
    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    if promo.get("limited", 0) >= promo.get("limit", 0):
        raise HTTPException(status_code=400, detail="Промокод исчерпан")
    
    # Check if user already used THIS promo
    used = await db.promo_logs.find_one({"user_id": user["id"], "promo_id": promo["id"]})
    if used:
        raise HTTPException(status_code=400, detail="Вы уже использовали этот промокод")
    
    # Check 24-hour cooldown - user can only use promo once per 24 hours
    last_promo = await db.promo_logs.find_one(
        {"user_id": user["id"]}, 
        sort=[("created_at", -1)]
    )
    if last_promo:
        last_time = datetime.fromisoformat(last_promo["created_at"].replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - last_time).total_seconds() < 86400:  # 24 hours
            hours_left = 24 - int((datetime.now(timezone.utc) - last_time).total_seconds() / 3600)
            raise HTTPException(status_code=400, detail=f"Промокоды можно использовать раз в 24 часа. Осталось: {hours_left} ч.")
    
    if promo.get("deposit_required") and user.get("total_deposited", 0) == 0:
        raise HTTPException(status_code=400, detail="Промокод доступен только после депозита")
    
    reward = promo.get("reward", 0)
    wager = reward * promo.get("wager_multiplier", 3) if promo.get("type") != 3 else 0
    
    # Add reward to PROMO balance (not deposit balance) - max withdrawal 300₽
    await db.users.update_one(
        {"id": user["id"]}, 
        {
            "$inc": {"balance": reward, "promo_balance": reward, "wager": wager},
            "$set": {"promo_withdrawal_limit": 300}  # Max 300₽ withdrawal from promo
        }
    )
    await db.promos.update_one({"id": promo["id"]}, {"$inc": {"limited": 1}})
    await db.promo_logs.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "promo_id": promo["id"],
        "promo_name": promo.get("name", ""),
        "reward": reward, "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"success": True, "reward": reward, "balance": user_data["balance"], "wager": wager}

# ================== HISTORY ==================

# Bot names for fake history
BOT_NAMES = [
    "Александр", "Михаил", "Дмитрий", "Артём", "Максим", "Иван", "Андрей", "Сергей",
    "Алексей", "Никита", "Владимир", "Кирилл", "Егор", "Павел", "Денис", "Роман",
    "Анна", "Мария", "Екатерина", "Елена", "Ольга", "Наталья", "Юлия", "Татьяна",
    "Lucky777", "WinMaster", "CasinoKing", "BigPlayer", "GoldHunter", "DiamondAce"
]

def generate_bot_history_item(game: str) -> dict:
    """Generate a fake history item for a bot player"""
    bot_name = random.choice(BOT_NAMES)
    
    if game == "mines":
        bet = random.choice([10, 25, 50, 100, 200, 500])
        coef = round(random.uniform(1.1, 5.0), 2)
        is_win = random.random() < 0.4
    elif game == "dice":
        bet = random.choice([10, 20, 50, 100, 250])
        coef = round(random.uniform(1.5, 5.0), 2)
        is_win = random.random() < 0.45
    elif game == "tower":
        bet = random.choice([10, 25, 50, 100])
        coef = random.choice([1.47, 2.18, 3.27, 7.34, 16.51])
        is_win = random.random() < 0.35
    elif game == "x100":
        bet = random.choice([10, 20, 50, 100, 200])
        coef = random.choice([2, 3, 10, 15, 20])
        is_win = random.random() < 0.3
    elif game == "crash":
        bet = random.choice([10, 25, 50, 100, 250])
        coef = round(random.uniform(1.2, 10.0), 2)
        is_win = random.random() < 0.4
    elif game == "bubbles":
        bet = random.choice([10, 25, 50, 100])
        coef = round(random.uniform(1.5, 5.0), 2)
        is_win = random.random() < 0.35
    else:
        bet = random.choice([10, 50, 100])
        coef = round(random.uniform(1.5, 3.0), 2)
        is_win = random.random() < 0.4
    
    win = round(bet * coef, 2) if is_win else 0
    
    return {
        "game": game,
        "name": bot_name,
        "bet": bet,
        "coefficient": coef if is_win else 0,
        "win": win,
        "status": "win" if is_win else "lose",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/history/recent")
async def get_recent_history(limit: int = Query(default=15, le=50)):
    history = []
    
    # Collect real history from all games
    game_collections = [
        ("mines_games", "mines", {"active": False}),
        ("dice_games", "dice", {}),
        ("tower_games", "tower", {"active": False}),
        ("x100_games", "x100", {}),
        ("crash_bets", "crash", {"status": {"$ne": "pending"}}),
        ("bubbles_games", "bubbles", {})
    ]
    
    for coll, game_name, query in game_collections:
        try:
            games = await db[coll].find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
            for g in games:
                user = await db.users.find_one({"id": g.get("user_id")}, {"_id": 0, "name": 1})
                if user:
                    coef = g.get("coef", g.get("coefficient", g.get("target", g.get("crash_point", 0))))
                    if not coef and g.get("bet") and g.get("win"):
                        coef = round(g.get("win", 0) / g.get("bet", 1), 2)
                    history.append({
                        "game": game_name, 
                        "name": user["name"], 
                        "bet": g.get("bet", 0), 
                        "coefficient": coef or 0,
                        "win": g.get("win", 0), 
                        "status": "win" if g.get("win", 0) > 0 else "lose", 
                        "created_at": g.get("created_at", datetime.now(timezone.utc).isoformat())
                    })
        except Exception:
            pass
    
    # Add bot history to mix in with real data (30-50% bots)
    bot_count = max(3, int(limit * 0.4))
    bot_games = ["mines", "dice", "tower", "x100", "crash", "bubbles"]
    for _ in range(bot_count):
        game = random.choice(bot_games)
        history.append(generate_bot_history_item(game))
    
    # Sort by created_at and return
    history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"success": True, "history": history[:limit]}

# ================== SOCIAL ==================

@api_router.get("/social")
async def get_social():
    return {"success": True, "social": {"telegram": "https://t.me/easymoneycaspro", "bot": "https://t.me/Irjeukdnr_bot"}}

# ================== ADMIN ==================

@api_router.post("/admin/login")
async def admin_login(request: Request, _=rate_limit("auth")):
    data = await request.json()
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    admin_token = jwt.encode({"admin": True, "exp": datetime.now(timezone.utc) + timedelta(hours=24)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"success": True, "token": admin_token}

@api_router.get("/admin/stats")
async def admin_stats(_: bool = Depends(verify_admin_token), __=rate_limit("admin")):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    all_payments = await db.payments.find({"status": "completed"}, {"_id": 0}).to_list(10000)
    payment_today = sum(p["amount"] for p in all_payments if p["created_at"] >= today.isoformat())
    payment_week = sum(p["amount"] for p in all_payments if p["created_at"] >= week_ago.isoformat())
    payment_all = sum(p["amount"] for p in all_payments)
    
    pending_withdraws = await db.withdraws.find({"status": "pending"}, {"_id": 0}).to_list(1000)
    
    users_all = await db.users.count_documents({})
    users_today = await db.users.count_documents({"created_at": {"$gte": today.isoformat()}})
    
    settings = await get_settings()
    
    return {
        "success": True,
        "payments": {"today": payment_today, "week": payment_week, "all": payment_all},
        "withdrawals": {"pending_count": len(pending_withdraws), "pending_sum": sum(w["amount"] for w in pending_withdraws)},
        "users": {"today": users_today, "all": users_all},
        "settings": settings
    }

@api_router.get("/admin/users")
async def admin_users(search: Optional[str] = None, page: int = 1, limit: int = 20, _: bool = Depends(verify_admin_token)):
    query = {}
    if search:
        # Try to parse as registration number (e.g., "900", "#900")
        search_clean = search.strip().replace("#", "")
        
        search_conditions = [
            {"name": {"$regex": search, "$options": "i"}},
            {"username": {"$regex": search, "$options": "i"}},
            {"id": {"$regex": search, "$options": "i"}}
        ]
        
        # If search is a number, also search by registration_number
        if search_clean.isdigit():
            search_conditions.append({"registration_number": int(search_clean)})
        
        query = {"$or": search_conditions}
    
    skip = (page - 1) * limit
    users = await db.users.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.users.count_documents(query)
    return {"success": True, "users": users, "total": total, "page": page, "pages": (total + limit - 1) // limit}

@api_router.put("/admin/user")
async def admin_update_user(request: Request, _: bool = Depends(verify_admin_token)):
    data = await request.json()
    user_id = data.pop("user_id", None)
    if user_id and data:
        await db.users.update_one({"id": user_id}, {"$set": data})
    return {"success": True}

@api_router.post("/admin/manual-deposit")
async def admin_manual_deposit(request: Request, _: bool = Depends(verify_admin_token)):
    """Admin endpoint to manually add deposit to user account
    
    This marks the deposit as manual so the user won't need min deposit for withdrawals.
    """
    data = await request.json()
    user_id = data.get("user_id")
    amount = float(data.get("amount", 0))
    note = data.get("note", "Ручное пополнение администратором")
    skip_wager = data.get("skip_wager", True)  # Don't add wager requirement
    
    if not user_id or amount <= 0:
        raise HTTPException(status_code=400, detail="Укажите user_id и сумму больше 0")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Create payment record for tracking
    payment_id = str(uuid.uuid4())
    payment = {
        "id": payment_id,
        "user_id": user_id,
        "amount": amount,
        "provider": "manual",
        "method": "admin",
        "status": "completed",
        "is_manual": True,  # Mark as manual - no min deposit requirement
        "note": note,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payments.insert_one(payment)
    
    # Update user balance using separate $inc and $set operations
    # IMPORTANT: Update both old balance field AND new deposit_balance for withdrawals
    inc_data = {
        "balance": amount,
        "deposit_balance": amount,  # Add to deposit_balance so user can withdraw
        "deposit": amount,
        "total_deposited": amount
    }
    if not skip_wager:
        inc_data["wager"] = amount * 3
    
    await db.users.update_one(
        {"id": user_id}, 
        {
            "$inc": inc_data,
            "$set": {"has_manual_deposit": True}  # Flag to skip min deposit checks
        }
    )
    
    # Calculate and add cashback for this deposit
    cashback = await calculate_deposit_cashback(user_id, amount)
    
    # Add referral bonus if user was invited
    await add_ref_bonus(user_id, amount)
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "balance": 1, "deposit": 1, "raceback": 1})
    
    logging.info(f"Admin manual deposit: {amount}₽ to user {user_id} (cashback: {cashback}₽)")
    
    return {
        "success": True,
        "payment_id": payment_id,
        "amount": amount,
        "new_balance": updated_user["balance"],
        "total_deposited": updated_user["deposit"],
        "cashback": cashback,
        "raceback": updated_user.get("raceback", 0),
        "message": f"Успешно начислено {amount}₽ пользователю (кешбек: {cashback}₽)"
    }

@api_router.put("/admin/rtp")
async def admin_update_rtp(request: Request, _: bool = Depends(verify_admin_token)):
    data = await request.json()
    update_data = {}
    
    for k, v in data.items():
        if v is not None and k.endswith("_rtp"):
            # Validate RTP range: 10% - 99.9%
            rtp_value = float(v)
            if rtp_value < 10 or rtp_value > 99.9:
                raise HTTPException(
                    status_code=400, 
                    detail=f"RTP для {k.replace('_rtp', '')} должен быть от 10% до 99.9%. Получено: {rtp_value}%"
                )
            update_data[k] = rtp_value
    
    if update_data:
        await db.settings.update_one({"id": "main"}, {"$set": update_data})
        logging.info(f"RTP settings updated: {update_data}")
    
    return {"success": True}

@api_router.get("/admin/settings")
async def admin_get_settings(_: bool = Depends(verify_admin_token)):
    settings = await get_settings()
    
    # Calculate actual RTP from statistics
    games = ["dice", "mines", "x100", "tower", "crash", "bubbles"]
    rtp_stats = {}
    
    for game in games:
        total_bets = settings.get(f"{game}_total_bets", 0)
        total_wins = settings.get(f"{game}_total_wins", 0)
        
        if total_bets > 0:
            actual_rtp = (total_wins / total_bets) * 100
            rtp_stats[game] = {
                "configured_rtp": settings.get(f"{game}_rtp", 97),
                "actual_rtp": round(actual_rtp, 2),
                "total_bets": total_bets,
                "total_wins": total_wins,
                "games_count": int(total_bets / 10) if total_bets > 0 else 0  # Approx games
            }
        else:
            rtp_stats[game] = {
                "configured_rtp": settings.get(f"{game}_rtp", 97),
                "actual_rtp": 0,
                "total_bets": 0,
                "total_wins": 0,
                "games_count": 0
            }
    
    return {"success": True, "settings": settings, "rtp_statistics": rtp_stats}

@api_router.put("/admin/settings")
async def admin_update_settings(request: Request, _: bool = Depends(verify_admin_token)):
    data = await request.json()
    update_data = {}
    
    for k, v in data.items():
        if v is None:
            continue
        
        # Validate RTP values
        if k.endswith("_rtp"):
            rtp_value = float(v)
            if rtp_value < 10 or rtp_value > 99.9:
                raise HTTPException(
                    status_code=400,
                    detail=f"RTP для {k.replace('_rtp', '')} должен быть от 10% до 99.9%. Получено: {rtp_value}%"
                )
            update_data[k] = rtp_value
        # Validate bank values
        elif k.endswith("_bank"):
            bank_value = float(v)
            if bank_value < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Банк не может быть отрицательным"
                )
            update_data[k] = bank_value
        else:
            update_data[k] = v
    
    if update_data:
        await db.settings.update_one({"id": "main"}, {"$set": update_data})
        logging.info(f"Settings updated: {list(update_data.keys())}")
    
    return {"success": True}

@api_router.get("/admin/promos")
async def admin_promos(page: int = 1, limit: int = 20, _: bool = Depends(verify_admin_token)):
    skip = (page - 1) * limit
    promos = await db.promos.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.promos.count_documents({})
    return {"success": True, "promos": promos, "total": total}

@api_router.post("/admin/promo")
async def admin_create_promo(request: Request, _: bool = Depends(verify_admin_token)):
    try:
        data = await request.json()
        
        # Validate required fields
        if not data.get("name"):
            raise HTTPException(status_code=400, detail="Название промокода обязательно")
        
        # Check if promo already exists
        existing = await db.promos.find_one({"name": data.get("name")})
        if existing:
            raise HTTPException(status_code=400, detail="Промокод уже существует")
        
        promo_type = int(data.get("type", 0))
        
        # Validate based on type
        if promo_type == 1:  # Percentage bonus
            bonus_percent = float(data.get("bonus_percent", 0))
            if bonus_percent <= 0 or bonus_percent > 100:
                raise HTTPException(status_code=400, detail="Процент бонуса должен быть от 1 до 100")
            reward = 0
        else:  # Fixed reward
            reward = float(data.get("reward", 0))
            if reward <= 0:
                raise HTTPException(status_code=400, detail="Сумма награды должна быть больше 0")
            bonus_percent = 0
        
        promo = {
            "id": str(uuid.uuid4()),
            "name": data.get("name"),
            "reward": reward,
            "limit": int(data.get("limit", 100)),
            "limited": 0,
            "type": promo_type,
            "deposit_required": data.get("deposit_required", False),
            "wager_multiplier": float(data.get("wager_multiplier", 3)),
            "bonus_percent": bonus_percent,
            "status": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.promos.insert_one(promo)
        logging.info(f"✅ Promo created: {promo['name']}, type={promo_type}, bonus={bonus_percent if promo_type == 1 else reward}")
        
        # Remove MongoDB _id before returning (it's added by insert_one)
        promo.pop("_id", None)
        return {"success": True, "promo": promo}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Error creating promo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания промокода: {str(e)}")

@api_router.get("/admin/withdraws")
async def admin_withdraws(status: str = "pending", page: int = 1, limit: int = 20, _: bool = Depends(verify_admin_token)):
    skip = (page - 1) * limit
    withdraws = await db.withdraws.find({"status": status}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    for w in withdraws:
        user = await db.users.find_one({"id": w["user_id"]}, {"_id": 0, "name": 1, "balance": 1, "username": 1})
        if user:
            w["user_name"] = user.get("name", "Unknown")
            w["user_balance"] = user.get("balance", 0)
            w["user_username"] = user.get("username", "")
    total = await db.withdraws.count_documents({"status": status})
    return {"success": True, "withdraws": withdraws, "total": total}

@api_router.post("/admin/withdraw/{withdraw_id}/approve")
async def admin_approve_withdraw(withdraw_id: str, request: Request, _: bool = Depends(verify_admin_token)):
    """Approve withdrawal - mark as completed"""
    withdraw = await db.withdraws.find_one({"id": withdraw_id}, {"_id": 0})
    if not withdraw:
        raise HTTPException(status_code=404, detail="Вывод не найден")
    
    if withdraw["status"] not in ["pending", "processing"]:
        raise HTTPException(status_code=400, detail=f"Невозможно подтвердить вывод со статусом: {withdraw['status']}")
    
    await db.withdraws.update_one(
        {"id": withdraw_id}, 
        {"$set": {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    logging.info(f"Withdrawal {withdraw_id} approved by admin")
    return {"success": True, "message": "Вывод подтвержден"}

@api_router.post("/admin/withdraw/{withdraw_id}/reject")
async def admin_reject_withdraw(withdraw_id: str, request: Request, _: bool = Depends(verify_admin_token)):
    """Reject withdrawal - return money to user"""
    data = await request.json() if request.headers.get("content-type") == "application/json" else {}
    comment = data.get("comment", "Отклонено администратором")
    
    withdraw = await db.withdraws.find_one({"id": withdraw_id}, {"_id": 0})
    if not withdraw:
        raise HTTPException(status_code=404, detail="Вывод не найден")
    
    if withdraw["status"] not in ["pending", "processing"]:
        raise HTTPException(status_code=400, detail=f"Невозможно отклонить вывод со статусом: {withdraw['status']}")
    
    # Return money to user
    await db.users.update_one(
        {"id": withdraw["user_id"]}, 
        {"$inc": {"balance": withdraw["amount"]}}
    )
    
    await db.withdraws.update_one(
        {"id": withdraw_id}, 
        {"$set": {
            "status": "rejected",
            "comment": comment,
            "rejected_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    logging.info(f"Withdrawal {withdraw_id} rejected by admin. Amount {withdraw['amount']} returned to user {withdraw['user_id']}")
    return {"success": True, "message": "Вывод отклонен, средства возвращены пользователю"}

@api_router.put("/admin/withdraw/{withdraw_id}")
async def admin_update_withdraw(withdraw_id: str, request: Request, _: bool = Depends(verify_admin_token)):
    """Legacy endpoint for updating withdrawal status"""
    data = await request.json()
    status = data.get("status", "")
    
    if not status:
        raise HTTPException(status_code=400, detail="Укажите статус")
    
    withdraw = await db.withdraws.find_one({"id": withdraw_id}, {"_id": 0})
    if not withdraw:
        raise HTTPException(status_code=404, detail="Вывод не найден")
    
    # If rejecting, return money to user
    if status == "rejected" and withdraw["status"] not in ["rejected", "completed"]:
        await db.users.update_one({"id": withdraw["user_id"]}, {"$inc": {"balance": withdraw["amount"]}})
        logging.info(f"Withdrawal {withdraw_id} rejected. Amount {withdraw['amount']} returned to user")
    
    update_data = {
        "status": status,
        "comment": data.get("comment", "")
    }
    
    if status == "completed":
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    elif status == "rejected":
        update_data["rejected_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.withdraws.update_one({"id": withdraw_id}, {"$set": update_data})
    return {"success": True, "message": f"Статус обновлен на: {status}"}

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Enable XSS filter
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Cache control for sensitive data
    if "/api/admin" in request.url.path or "/api/auth" in request.url.path:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
