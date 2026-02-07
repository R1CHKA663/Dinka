#!/usr/bin/env python3
"""
EASY MONEY Casino - Load Testing Script
Нагрузочное тестирование с использованием asyncio + aiohttp

Использование:
    python3 load_test.py --users 50 --duration 60 --rps 10
    
Параметры:
    --users     Количество виртуальных пользователей (default: 50)
    --duration  Продолжительность теста в секундах (default: 60)
    --rps       Запросов в секунду на пользователя (default: 5)
"""

import asyncio
import aiohttp
import argparse
import time
import random
import json
import statistics
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Any

# Configuration
API_BASE_URL = "https://referfix.preview.emergentagent.com/api"

# Rate limits на сервере (per IP per minute)
SERVER_RATE_LIMITS = {
    "auth": 30,      # 30 auth attempts
    "games": 300,    # 300 game plays
    "default": 500   # 500 requests
}

@dataclass
class TestResult:
    endpoint: str
    status: int
    response_time: float
    success: bool
    error: str = ""

@dataclass
class LoadTestStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    endpoint_stats: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    
    @property
    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
    
    @property
    def avg_response_time(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0
    
    @property
    def p50_response_time(self) -> float:
        return statistics.median(self.response_times) if self.response_times else 0
    
    @property
    def p95_response_time(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]
    
    @property
    def p99_response_time(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]


class VirtualUser:
    """Симулирует реального пользователя казино"""
    
    def __init__(self, user_id: int, session: aiohttp.ClientSession, stats: LoadTestStats):
        self.user_id = user_id
        self.session = session
        self.stats = stats
        self.token = None
        self.user_data = None
        self.balance = 1000.0
        
    async def login(self) -> bool:
        """Авторизация демо-пользователя"""
        try:
            username = f"loadtest_user_{self.user_id}_{int(time.time())}"
            start = time.time()
            
            async with self.session.post(
                f"{API_BASE_URL}/auth/demo",
                json={"username": username},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                response_time = time.time() - start
                data = await resp.json()
                
                self.stats.total_requests += 1
                self.stats.response_times.append(response_time)
                self.stats.endpoint_stats["/auth/demo"].append(response_time)
                
                if resp.status == 200 and data.get("success"):
                    self.token = data["token"]
                    self.user_data = data["user"]
                    self.balance = self.user_data.get("balance", 1000.0)
                    self.stats.successful_requests += 1
                    return True
                else:
                    self.stats.failed_requests += 1
                    self.stats.errors["auth_failed"] += 1
                    return False
                    
        except Exception as e:
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.errors[str(type(e).__name__)] += 1
            return False
    
    async def make_request(self, method: str, endpoint: str, json_data: dict = None) -> TestResult:
        """Выполняет HTTP запрос с авторизацией"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
        try:
            start = time.time()
            
            if method == "GET":
                async with self.session.get(
                    f"{API_BASE_URL}{endpoint}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    response_time = time.time() - start
                    await resp.json()
                    
                    return TestResult(
                        endpoint=endpoint,
                        status=resp.status,
                        response_time=response_time,
                        success=resp.status == 200
                    )
            else:
                async with self.session.post(
                    f"{API_BASE_URL}{endpoint}",
                    headers=headers,
                    json=json_data or {},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    response_time = time.time() - start
                    await resp.json()
                    
                    return TestResult(
                        endpoint=endpoint,
                        status=resp.status,
                        response_time=response_time,
                        success=resp.status == 200
                    )
                    
        except asyncio.TimeoutError:
            return TestResult(endpoint=endpoint, status=0, response_time=15.0, success=False, error="Timeout")
        except Exception as e:
            return TestResult(endpoint=endpoint, status=0, response_time=0, success=False, error=str(e))
    
    async def play_dice(self) -> TestResult:
        """Играет в Dice"""
        bet = random.choice([10, 20, 50, 100])
        target = random.randint(1, 100)
        is_over = random.choice([True, False])
        
        return await self.make_request("POST", "/games/dice/play", {
            "bet": bet,
            "target": target,
            "isOver": is_over
        })
    
    async def play_bubbles(self) -> TestResult:
        """Играет в Bubbles"""
        bet = random.choice([10, 20, 50, 100])
        color = random.choice(["blue", "green", "purple", "yellow", "red"])
        
        return await self.make_request("POST", "/games/bubbles/play", {
            "bet": bet,
            "color": color
        })
    
    async def play_x100(self) -> TestResult:
        """Играет в X100"""
        bet = random.choice([10, 20, 50])
        sector = random.randint(0, 99)
        
        return await self.make_request("POST", "/games/x100/play", {
            "bet": bet,
            "sector": sector
        })
    
    async def get_history(self) -> TestResult:
        """Получает историю игр"""
        return await self.make_request("GET", "/history/recent?limit=15")
    
    async def get_profile(self) -> TestResult:
        """Получает профиль"""
        return await self.make_request("GET", "/auth/me")
    
    async def get_online(self) -> TestResult:
        """Получает количество онлайн"""
        return await self.make_request("GET", "/online")
    
    async def simulate_session(self, duration: int, rps: float):
        """Симулирует игровую сессию пользователя"""
        if not await self.login():
            return
        
        end_time = time.time() + duration
        interval = 1.0 / rps
        
        # Доступные действия с весами
        actions = [
            (self.play_dice, 30),      # 30% - играть в Dice
            (self.play_bubbles, 25),   # 25% - играть в Bubbles
            (self.play_x100, 15),      # 15% - играть в X100
            (self.get_history, 15),    # 15% - смотреть историю
            (self.get_profile, 10),    # 10% - смотреть профиль
            (self.get_online, 5),      # 5% - проверять онлайн
        ]
        
        total_weight = sum(w for _, w in actions)
        
        while time.time() < end_time:
            # Выбираем случайное действие на основе весов
            rand = random.randint(1, total_weight)
            cumulative = 0
            selected_action = None
            
            for action, weight in actions:
                cumulative += weight
                if rand <= cumulative:
                    selected_action = action
                    break
            
            if selected_action:
                result = await selected_action()
                
                self.stats.total_requests += 1
                self.stats.response_times.append(result.response_time)
                self.stats.endpoint_stats[result.endpoint].append(result.response_time)
                
                if result.success:
                    self.stats.successful_requests += 1
                else:
                    self.stats.failed_requests += 1
                    if result.error:
                        self.stats.errors[result.error] += 1
                    else:
                        self.stats.errors[f"HTTP_{result.status}"] += 1
            
            # Ждём до следующего запроса
            await asyncio.sleep(interval + random.uniform(-0.1, 0.1))


async def run_load_test(num_users: int, duration: int, rps: float):
    """Запускает нагрузочное тестирование"""
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║          EASY MONEY Casino - Load Testing                        ║
╠══════════════════════════════════════════════════════════════════╣
║  Пользователей: {num_users:<10}                                       ║
║  Продолжительность: {duration} сек                                      ║
║  RPS на пользователя: {rps}                                            ║
║  Ожидаемый RPS: ~{num_users * rps:.0f}                                           ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    stats = LoadTestStats()
    
    connector = aiohttp.TCPConnector(
        limit=num_users * 2,
        limit_per_host=num_users * 2,
        ttl_dns_cache=300
    )
    
    async with aiohttp.ClientSession(connector=connector) as session:
        users = [VirtualUser(i, session, stats) for i in range(num_users)]
        
        start_time = time.time()
        print(f"🚀 Запуск теста в {datetime.now().strftime('%H:%M:%S')}...")
        print(f"⏳ Ожидайте ~{duration} секунд...\n")
        
        # Запускаем всех пользователей параллельно
        await asyncio.gather(*[
            user.simulate_session(duration, rps) 
            for user in users
        ])
        
        elapsed = time.time() - start_time
    
    # Вывод результатов
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ                       ║
╠══════════════════════════════════════════════════════════════════╣
║  Время теста: {elapsed:.1f} сек                                          ║
║  Всего запросов: {stats.total_requests}                                       ║
║  Успешных: {stats.successful_requests} ({stats.success_rate:.1f}%)                                    ║
║  Неудачных: {stats.failed_requests}                                             ║
║  Фактический RPS: {stats.total_requests / elapsed:.1f}                                        ║
╠══════════════════════════════════════════════════════════════════╣
║                    ВРЕМЯ ОТВЕТА                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Среднее: {stats.avg_response_time * 1000:.0f} ms                                          ║
║  P50: {stats.p50_response_time * 1000:.0f} ms                                              ║
║  P95: {stats.p95_response_time * 1000:.0f} ms                                              ║
║  P99: {stats.p99_response_time * 1000:.0f} ms                                              ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Статистика по эндпоинтам
    print("📊 Статистика по эндпоинтам:")
    print("-" * 60)
    for endpoint, times in sorted(stats.endpoint_stats.items()):
        avg = statistics.mean(times) * 1000
        count = len(times)
        print(f"  {endpoint:<30} | {count:>5} запросов | {avg:>6.0f} ms avg")
    
    # Ошибки
    if stats.errors:
        print("\n⚠️ Ошибки:")
        print("-" * 60)
        for error, count in sorted(stats.errors.items(), key=lambda x: -x[1]):
            print(f"  {error:<40} | {count:>5}")
    
    # Оценка
    print("\n" + "=" * 60)
    if stats.success_rate >= 99 and stats.p95_response_time < 1.0:
        print("✅ ОТЛИЧНО: Система стабильна под нагрузкой!")
    elif stats.success_rate >= 95 and stats.p95_response_time < 2.0:
        print("⚠️ ХОРОШО: Небольшие проблемы при пиковой нагрузке")
    elif stats.success_rate >= 90:
        print("⚠️ УДОВЛЕТВОРИТЕЛЬНО: Рекомендуется оптимизация")
    else:
        print("❌ ТРЕБУЕТСЯ ОПТИМИЗАЦИЯ: Много ошибок/таймаутов")
    print("=" * 60)
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="EASY MONEY Casino - Load Testing")
    parser.add_argument("--users", type=int, default=50, help="Количество виртуальных пользователей")
    parser.add_argument("--duration", type=int, default=60, help="Продолжительность теста в секундах")
    parser.add_argument("--rps", type=float, default=5, help="Запросов в секунду на пользователя")
    
    args = parser.parse_args()
    
    asyncio.run(run_load_test(args.users, args.duration, args.rps))


if __name__ == "__main__":
    main()
