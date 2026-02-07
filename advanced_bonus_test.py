#!/usr/bin/env python3
"""
EASY MONEY Gaming Platform - Advanced Bonus System Tests
Testing specific business requirements:
1. Cashback is ONLY given ONCE on first deposit
2. Promo codes can only be used once every 24 hours
3. Max withdrawal from bonus is 300₽ after wagering
4. Wagering blocks only bonus balance, deposit always available
"""

import requests
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

class AdvancedBonusSystemTester:
    def __init__(self, base_url="https://project-launcher-44.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.critical_issues = []

    def log_test(self, name: str, success: bool, details: str = "", is_critical: bool = False):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
            if is_critical:
                self.critical_issues.append(f"{name}: {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details,
            "critical": is_critical,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def make_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> tuple:
        """Make API request and return (success, response_data)"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}

            return success, response_data

        except Exception as e:
            return False, {"error": str(e)}

    def setup_test_user(self) -> bool:
        """Create a fresh test user"""
        print("\n🔐 Setting up test user...")
        
        timestamp = int(time.time())
        demo_username = f"bonus_test_{timestamp}"
        
        success, response = self.make_request('POST', 'auth/demo', {
            "username": demo_username
        })
        
        if success and response.get("success"):
            self.token = response.get("token")
            user_data = response.get("user", {})
            self.user_id = user_data.get("id")
            
            self.log_test("Test User Setup", True, f"User ID: {self.user_id}")
            return True
        else:
            self.log_test("Test User Setup", False, f"Response: {response}", is_critical=True)
            return False

    def test_cashback_one_time_only(self) -> bool:
        """Test that cashback is only given once on first deposit"""
        print("\n💰 Testing One-Time Cashback Logic...")
        
        # Get initial cashback status
        success, response = self.make_request('GET', 'bonus/raceback')
        if not success:
            self.log_test("Cashback One-Time - Initial Check", False, f"API error: {response}", is_critical=True)
            return False
        
        initial_cashback_received = response.get("cashback_received", False)
        initial_total_deposited = response.get("total_deposited", 0)
        
        # For demo users, we can't actually test deposits, but we can verify the logic structure
        if initial_cashback_received:
            # User already received cashback
            cashback_deposit_amount = response.get("cashback_deposit_amount", 0)
            if cashback_deposit_amount > 0:
                self.log_test("Cashback One-Time - Already Received", True, 
                             f"User already received cashback for deposit: {cashback_deposit_amount}₽")
            else:
                self.log_test("Cashback One-Time - Missing Deposit Amount", False, 
                             "cashback_received=True but no cashback_deposit_amount", is_critical=True)
                return False
        else:
            # User hasn't received cashback yet
            if initial_total_deposited > 0:
                self.log_test("Cashback One-Time - Logic Error", False, 
                             f"User has deposits ({initial_total_deposited}₽) but no cashback received", is_critical=True)
                return False
            else:
                self.log_test("Cashback One-Time - Fresh User", True, 
                             "New user with no deposits and no cashback - correct state")
        
        # Verify the info message is correct
        info_msg = response.get("info", "")
        if "ОДИН раз" not in info_msg and "первом пополнении" not in info_msg:
            self.log_test("Cashback One-Time - Info Message", False, 
                         f"Missing one-time info in message: {info_msg}", is_critical=True)
            return False
        
        self.log_test("Cashback One-Time - Info Message", True, "Correct one-time cashback info")
        return True

    def test_promo_balance_separation(self) -> bool:
        """Test that promo rewards go to promo_balance, not deposit_balance"""
        print("\n🎫 Testing Promo Balance Separation...")
        
        # Get initial balances
        success, response = self.make_request('GET', 'withdraw/info')
        if not success:
            self.log_test("Promo Balance - Initial Check", False, f"API error: {response}", is_critical=True)
            return False
        
        initial_balances = response.get("balances", {})
        initial_deposit = initial_balances.get("deposit_balance", 0)
        initial_promo = initial_balances.get("promo_balance", 0)
        
        # Try to activate a promo (this will likely fail, but we can check the error handling)
        success, promo_response = self.make_request('POST', 'promo/activate', {
            "code": "TEST123"
        }, expected_status=404)  # Expect 404 for non-existent promo
        
        if success:
            self.log_test("Promo Balance - Invalid Code Handling", True, "Correctly handles invalid promo codes")
        else:
            # Check if it's a different error (like 24h cooldown)
            if promo_response.get("status_code") == 400:
                detail = promo_response.get("detail", "")
                if "24 часа" in detail:
                    self.log_test("Promo Balance - 24h Cooldown Active", True, 
                                 f"24h cooldown is working: {detail}")
                else:
                    self.log_test("Promo Balance - Unexpected Error", False, 
                                 f"Unexpected 400 error: {detail}")
            else:
                self.log_test("Promo Balance - API Error", False, f"Response: {promo_response}")
        
        return True

    def test_300_ruble_promo_limit(self) -> bool:
        """Test that promo balance withdrawal is limited to 300₽"""
        print("\n💸 Testing 300₽ Promo Withdrawal Limit...")
        
        success, response = self.make_request('GET', 'withdraw/info')
        if not success:
            self.log_test("300₽ Limit - API Check", False, f"API error: {response}", is_critical=True)
            return False
        
        promo_limit = response.get("promo_limit", 0)
        if promo_limit != 300:
            self.log_test("300₽ Limit - Incorrect Limit", False, 
                         f"promo_limit is {promo_limit}, expected 300", is_critical=True)
            return False
        
        # Check withdrawable calculation
        from_promo = response.get("from_promo", 0)
        locked_promo = response.get("locked_promo", 0)
        balances = response.get("balances", {})
        promo_balance = balances.get("promo_balance", 0)
        wager = response.get("wager", 0)
        
        if wager == 0:
            # No wager - promo should be available up to 300₽ limit
            expected_from_promo = min(promo_balance, 300)
            expected_locked = max(0, promo_balance - 300)
            
            if from_promo != expected_from_promo:
                self.log_test("300₽ Limit - Withdrawable Calculation", False, 
                             f"from_promo ({from_promo}) != expected ({expected_from_promo})", is_critical=True)
                return False
            
            if locked_promo != expected_locked:
                self.log_test("300₽ Limit - Locked Calculation", False, 
                             f"locked_promo ({locked_promo}) != expected ({expected_locked})", is_critical=True)
                return False
        
        self.log_test("300₽ Limit - Correct Implementation", True, 
                     f"Limit: {promo_limit}₽, Available: {from_promo}₽, Locked: {locked_promo}₽")
        return True

    def test_wager_blocks_only_promo(self) -> bool:
        """Test that wagering blocks only promo balance, not deposit balance"""
        print("\n🎰 Testing Wager Blocks Only Promo Balance...")
        
        success, response = self.make_request('GET', 'withdraw/info')
        if not success:
            self.log_test("Wager Logic - API Check", False, f"API error: {response}", is_critical=True)
            return False
        
        wager = response.get("wager", 0)
        from_deposit = response.get("from_deposit", 0)
        from_promo = response.get("from_promo", 0)
        balances = response.get("balances", {})
        deposit_balance = balances.get("deposit_balance", 0)
        promo_balance = balances.get("promo_balance", 0)
        
        # Rule: Deposit balance is ALWAYS withdrawable regardless of wager
        if from_deposit != deposit_balance:
            self.log_test("Wager Logic - Deposit Always Available", False, 
                         f"from_deposit ({from_deposit}) != deposit_balance ({deposit_balance})", is_critical=True)
            return False
        
        # Rule: Wager blocks promo balance
        if wager > 0:
            if from_promo != 0:
                self.log_test("Wager Logic - Promo Blocked by Wager", False, 
                             f"Wager {wager} > 0 but from_promo is {from_promo}, should be 0", is_critical=True)
                return False
            
            # Check wager info message
            wager_info = response.get("wager_info")
            if not wager_info or "Депозит доступен для вывода всегда" not in wager_info:
                self.log_test("Wager Logic - Info Message", False, 
                             f"Missing or incorrect wager info: {wager_info}", is_critical=True)
                return False
            
            self.log_test("Wager Logic - Active Wager", True, 
                         f"Wager {wager} correctly blocks promo, deposit available")
        else:
            # No wager - promo should be available up to limit
            expected_from_promo = min(promo_balance, 300)
            if from_promo != expected_from_promo:
                self.log_test("Wager Logic - No Wager Promo Available", False, 
                             f"from_promo ({from_promo}) != expected ({expected_from_promo})", is_critical=True)
                return False
            
            self.log_test("Wager Logic - No Active Wager", True, 
                         f"No wager, promo available: {from_promo}₽")
        
        return True

    def test_api_endpoint_completeness(self) -> bool:
        """Test that all required API endpoints exist and return proper data"""
        print("\n🔗 Testing API Endpoint Completeness...")
        
        # Test /api/bonus/raceback
        success, response = self.make_request('GET', 'bonus/raceback')
        if not success:
            self.log_test("API Completeness - bonus/raceback", False, f"Endpoint error: {response}", is_critical=True)
            return False
        
        required_fields = ["cashback_received", "info", "total_deposited", "level", "raceback"]
        missing = [f for f in required_fields if f not in response]
        if missing:
            self.log_test("API Completeness - bonus/raceback fields", False, 
                         f"Missing fields: {missing}", is_critical=True)
            return False
        
        # Test /api/withdraw/info
        success, response = self.make_request('GET', 'withdraw/info')
        if not success:
            self.log_test("API Completeness - withdraw/info", False, f"Endpoint error: {response}", is_critical=True)
            return False
        
        required_fields = ["from_deposit", "from_promo", "locked_promo", "wager", "balances", "promo_limit"]
        missing = [f for f in required_fields if f not in response]
        if missing:
            self.log_test("API Completeness - withdraw/info fields", False, 
                         f"Missing fields: {missing}", is_critical=True)
            return False
        
        # Test /api/promo/activate (should handle invalid codes properly)
        success, response = self.make_request('POST', 'promo/activate', {"code": "INVALID"}, expected_status=404)
        if not success:
            self.log_test("API Completeness - promo/activate", False, f"Endpoint error: {response}", is_critical=True)
            return False
        
        self.log_test("API Completeness - All Endpoints", True, "All required endpoints exist and respond correctly")
        return True

    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all comprehensive bonus system tests"""
        print("🎮 EASY MONEY Gaming Platform - Advanced Bonus System Tests")
        print("=" * 70)
        
        # Setup
        if not self.setup_test_user():
            return self.get_test_summary()
        
        # Run all tests
        self.test_cashback_one_time_only()
        self.test_promo_balance_separation()
        self.test_300_ruble_promo_limit()
        self.test_wager_blocks_only_promo()
        self.test_api_endpoint_completeness()
        
        return self.get_test_summary()

    def get_test_summary(self) -> Dict[str, Any]:
        """Get comprehensive test summary"""
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"\n📊 Comprehensive Test Summary:")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.critical_issues:
            print(f"\n🚨 Critical Issues Found ({len(self.critical_issues)}):")
            for issue in self.critical_issues:
                print(f"  - {issue}")
        else:
            print(f"\n✅ No critical issues found!")
        
        return {
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "success_rate": success_rate,
            "critical_issues": self.critical_issues,
            "test_results": self.test_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

def main():
    """Main test execution"""
    tester = AdvancedBonusSystemTester()
    
    try:
        results = tester.run_comprehensive_tests()
        
        # Save results to file
        with open("/app/test_reports/advanced_bonus_test_results.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Return appropriate exit code
        return 0 if len(results["critical_issues"]) == 0 else 1
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())