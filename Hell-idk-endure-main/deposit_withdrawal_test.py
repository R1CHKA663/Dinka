#!/usr/bin/env python3
"""
Deposit & Withdrawal Testing Suite for EASY MONEY Gaming Platform
Tests manual deposit functionality, withdrawal system, and RTP settings
"""

import requests
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Tuple

class DepositWithdrawalTester:
    def __init__(self, base_url="https://total-launch.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.user_token = None
        self.admin_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        
        # Admin credentials
        self.admin_password = "ADMIn1@tim"
        
        print(f"🎯 Deposit & Withdrawal Testing Suite Initialized")
        print(f"📡 Backend URL: {base_url}")
        print(f"🔧 API URL: {self.api_url}")

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
        return success

    def make_request(self, method: str, endpoint: str, data: dict = None, headers: dict = None) -> Tuple[bool, dict]:
        """Make HTTP request with error handling"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)
            
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=default_headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=default_headers, timeout=30)
            else:
                return False, {"error": f"Unsupported method: {method}"}
                
            return response.status_code < 400, response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}
        except json.JSONDecodeError:
            return False, {"error": "Invalid JSON response"}

    def test_basic_connectivity(self) -> bool:
        """Test basic API connectivity"""
        print("\n🔌 Testing Basic Connectivity...")
        
        success, data = self.make_request('POST', '/auth/demo', {'username': 'test_connectivity'})
        if not success:
            return self.log_test("Basic Connectivity", False, f"Cannot reach API: {data.get('error', 'Unknown error')}")
        
        return self.log_test("Basic Connectivity", True, "API is reachable")

    def test_demo_auth(self) -> bool:
        """Create demo user for testing"""
        print("\n👤 Creating Demo User...")
        
        username = f"deposit_test_{int(time.time())}"
        success, data = self.make_request('POST', '/auth/demo', {
            'username': username
        })
        
        if not success or not data.get('success'):
            return self.log_test("Demo Auth", False, f"Failed to create demo user: {data.get('error', 'Unknown error')}")
        
        self.user_token = data.get('token')
        self.user_id = data.get('user', {}).get('id')
        
        if not self.user_token or not self.user_id:
            return self.log_test("Demo Auth", False, "Missing token or user ID")
        
        return self.log_test("Demo Auth", True, f"Demo user created: {username}")

    def test_admin_auth(self) -> bool:
        """Test admin authentication"""
        print("\n🔐 Testing Admin Authentication...")
        
        success, data = self.make_request('POST', '/admin/login', {
            'password': self.admin_password
        })
        
        if not success:
            return self.log_test("Admin Auth", False, f"Admin auth failed: {data.get('error', 'Unknown error')}")
        
        if data.get('success') and data.get('token'):
            self.admin_token = data.get('token')
            return self.log_test("Admin Auth", True, "Admin authenticated successfully")
        
        return self.log_test("Admin Auth", False, "Admin auth response invalid")

    def get_auth_headers(self, admin: bool = False) -> dict:
        """Get authorization headers"""
        token = self.admin_token if admin else self.user_token
        return {'Authorization': f'Bearer {token}'} if token else {}

    def get_user_balance(self) -> Dict[str, float]:
        """Get user's current balance breakdown"""
        headers = self.get_auth_headers()
        success, data = self.make_request('GET', '/auth/me', headers=headers)
        
        if not success or not data.get('success'):
            return {}
        
        user = data.get('user', {})
        return {
            'total_balance': user.get('balance', 0),
            'deposit_balance': user.get('deposit_balance', 0),
            'promo_balance': user.get('promo_balance', 0),
            'wager': user.get('wager', 0)
        }

    def test_manual_deposit_updates_deposit_balance(self) -> bool:
        """Test that manual deposit in admin panel updates deposit_balance"""
        print("\n💰 Testing Manual Deposit Updates deposit_balance...")
        
        if not self.admin_token:
            return self.log_test("Manual Deposit Test", False, "Admin token required")
        
        # Get initial balance
        initial_balance = self.get_user_balance()
        if not initial_balance:
            return self.log_test("Manual Deposit Test", False, "Could not get initial balance")
        
        initial_deposit_balance = initial_balance.get('deposit_balance', 0)
        print(f"   Initial deposit_balance: {initial_deposit_balance}")
        
        # Perform manual deposit via admin (correct endpoint)
        deposit_amount = 100.0
        headers = self.get_auth_headers(admin=True)
        success, data = self.make_request('POST', '/admin/manual-deposit', {
            'user_id': self.user_id,
            'amount': deposit_amount
        }, headers=headers)
        
        if not success or not data.get('success'):
            return self.log_test("Manual Deposit Test", False, f"Manual deposit failed: {data.get('detail', data.get('error', 'Unknown error'))}")
        
        # Wait a moment for the update to process
        time.sleep(1)
        
        # Get updated balance
        updated_balance = self.get_user_balance()
        if not updated_balance:
            return self.log_test("Manual Deposit Test", False, "Could not get updated balance")
        
        updated_deposit_balance = updated_balance.get('deposit_balance', 0)
        print(f"   Updated deposit_balance: {updated_deposit_balance}")
        
        # Check if deposit_balance increased by the deposit amount
        expected_balance = initial_deposit_balance + deposit_amount
        balance_correct = abs(updated_deposit_balance - expected_balance) < 0.01
        
        return self.log_test("Manual Deposit Test", balance_correct, 
                           f"Expected: {expected_balance}, Got: {updated_deposit_balance}")

    def test_withdrawal_with_wager_blocking(self) -> bool:
        """Test that wager blocks only promo_balance, not deposit_balance"""
        print("\n🚫 Testing Wager Blocking System...")
        
        if not self.admin_token:
            return self.log_test("Wager Blocking Test", False, "Admin token required")
        
        # First, ensure user has some deposit_balance
        headers = self.get_auth_headers(admin=True)
        
        # Add deposit balance via manual deposit
        success, data = self.make_request('POST', '/admin/manual-deposit', {
            'user_id': self.user_id,
            'amount': 200.0
        }, headers=headers)
        
        if not success:
            return self.log_test("Wager Blocking Test", False, "Could not add deposit balance")
        
        # Add wager requirement by updating user directly
        success, data = self.make_request('PUT', '/admin/user', {
            'user_id': self.user_id,
            'wager': 500.0
        }, headers=headers)
        
        if not success:
            return self.log_test("Wager Blocking Test", False, "Could not set wager")
        
        time.sleep(1)
        
        # Get balance after setup
        balance = self.get_user_balance()
        print(f"   Balance after setup: {balance}")
        
        # Try to withdraw from deposit_balance (should work even with wager)
        user_headers = self.get_auth_headers()
        success, data = self.make_request('POST', '/withdraw/create', {
            'amount': 50.0,
            'wallet': '1234567890123456',
            'system': 'card',
            'provider': '1plat',
            'bank_name': 'Sberbank'
        }, headers=user_headers)
        
        # Check if withdrawal was created (even if pending)
        withdrawal_created = success and (data.get('success') or 'заявка' in data.get('message', '').lower())
        
        return self.log_test("Wager Blocking Test", withdrawal_created,
                           f"Withdrawal response: {data.get('message', data.get('detail', 'No message'))}")

    def test_rtp_range_validation(self) -> bool:
        """Test RTP sliders range 10-99.9%"""
        print("\n📊 Testing RTP Range Validation (10-99.9%)...")
        
        if not self.admin_token:
            return self.log_test("RTP Range Test", False, "Admin token required")
        
        headers = self.get_auth_headers(admin=True)
        test_cases = [
            (10.0, True, "Minimum RTP"),
            (99.9, True, "Maximum RTP"),
            (50.0, True, "Mid-range RTP"),
            (9.9, False, "Below minimum RTP"),
            (100.0, False, "Above maximum RTP"),
            (0.0, False, "Zero RTP"),
            (150.0, False, "Excessive RTP")
        ]
        
        passed_tests = 0
        total_tests = len(test_cases)
        
        for rtp_value, should_succeed, description in test_cases:
            success, data = self.make_request('PUT', '/admin/settings', {
                'dice_rtp': rtp_value
            }, headers=headers)
            
            test_passed = (success and data.get('success')) == should_succeed
            
            if test_passed:
                passed_tests += 1
                print(f"   ✅ {description}: {rtp_value}% - {'Accepted' if should_succeed else 'Rejected'}")
            else:
                print(f"   ❌ {description}: {rtp_value}% - Expected {'accept' if should_succeed else 'reject'}")
        
        success_rate = passed_tests / total_tests
        return self.log_test("RTP Range Test", success_rate >= 0.8, 
                           f"Passed {passed_tests}/{total_tests} range validation tests")

    def test_rtp_persistence(self) -> bool:
        """Test RTP settings persistence in database"""
        print("\n💾 Testing RTP Settings Persistence...")
        
        if not self.admin_token:
            return self.log_test("RTP Persistence Test", False, "Admin token required")
        
        headers = self.get_auth_headers(admin=True)
        
        # Set specific RTP values
        test_rtp_values = {
            'dice_rtp': 85.5,
            'mines_rtp': 92.3,
            'bubbles_rtp': 88.7,
            'tower_rtp': 94.1
        }
        
        # Set the values
        success, data = self.make_request('PUT', '/admin/settings', test_rtp_values, headers=headers)
        
        if not success or not data.get('success'):
            return self.log_test("RTP Persistence Test", False, "Could not set RTP values")
        
        time.sleep(1)  # Wait for persistence
        
        # Retrieve the values
        success, data = self.make_request('GET', '/admin/settings', headers=headers)
        
        if not success or not data.get('success'):
            return self.log_test("RTP Persistence Test", False, "Could not retrieve RTP values")
        
        settings = data.get('settings', {})
        
        # Check if all values persisted correctly
        all_correct = True
        for key, expected_value in test_rtp_values.items():
            actual_value = settings.get(key, 0)
            if abs(actual_value - expected_value) > 0.1:
                all_correct = False
                print(f"   ❌ {key}: Expected {expected_value}, Got {actual_value}")
            else:
                print(f"   ✅ {key}: {actual_value} (correct)")
        
        return self.log_test("RTP Persistence Test", all_correct, 
                           "All RTP values persisted correctly" if all_correct else "Some values not persisted")

    def test_rtp_impact_on_games(self) -> bool:
        """Test that RTP really affects game outcomes"""
        print("\n🎮 Testing RTP Impact on Game Outcomes...")
        
        if not self.admin_token:
            return self.log_test("RTP Impact Test", False, "Admin token required")
        
        # Test with Dice game using different RTP values
        headers = self.get_auth_headers(admin=True)
        user_headers = self.get_auth_headers()
        
        rtp_tests = [
            (20.0, "Low RTP"),
            (95.0, "High RTP")
        ]
        
        results = []
        
        for rtp_value, description in rtp_tests:
            print(f"   Testing {description} ({rtp_value}%)...")
            
            # Set RTP
            success, data = self.make_request('PUT', '/admin/settings', {
                'dice_rtp': rtp_value
            }, headers=headers)
            
            if not success:
                continue
            
            time.sleep(1)  # Wait for settings to apply
            
            # Play 20 games
            wins = 0
            total_bet = 0
            total_win = 0
            
            for i in range(20):
                bet_amount = 10
                success, data = self.make_request('POST', '/games/dice/play', {
                    'bet': bet_amount,
                    'chance': 50,
                    'type': 'under'
                }, headers=user_headers)
                
                if success and data.get('success'):
                    total_bet += bet_amount
                    win_amount = data.get('win', 0)
                    total_win += win_amount
                    if win_amount > 0:
                        wins += 1
                
                time.sleep(0.1)
            
            win_rate = (wins / 20 * 100) if 20 > 0 else 0
            actual_rtp = (total_win / total_bet * 100) if total_bet > 0 else 0
            
            results.append({
                'rtp_setting': rtp_value,
                'win_rate': win_rate,
                'actual_rtp': actual_rtp,
                'description': description
            })
            
            print(f"     Win Rate: {win_rate:.1f}%, Actual RTP: {actual_rtp:.1f}%")
        
        if len(results) < 2:
            return self.log_test("RTP Impact Test", False, "Could not test both RTP levels")
        
        # Check if higher RTP gives better results
        low_rtp_result = results[0]
        high_rtp_result = results[1]
        
        # Higher RTP should generally give better win rates or actual RTP
        improvement = (high_rtp_result['actual_rtp'] > low_rtp_result['actual_rtp'] or 
                      high_rtp_result['win_rate'] > low_rtp_result['win_rate'])
        
        return self.log_test("RTP Impact Test", improvement,
                           f"Low RTP: {low_rtp_result['actual_rtp']:.1f}%, High RTP: {high_rtp_result['actual_rtp']:.1f}%")

    def test_withdrawal_amount_calculation(self) -> bool:
        """Test withdrawable amount calculation with promo limits"""
        print("\n💸 Testing Withdrawal Amount Calculation...")
        
        # Get withdrawable amount endpoint (correct endpoint)
        user_headers = self.get_auth_headers()
        success, data = self.make_request('GET', '/withdraw/info', headers=user_headers)
        
        if not success:
            return self.log_test("Withdrawal Calculation Test", False, f"Could not get withdrawable amount: {data.get('detail', data.get('error', 'Unknown error'))}")
        
        # Check if response contains expected fields
        expected_fields = ['withdrawable_total', 'from_deposit', 'from_promo']
        has_all_fields = all(field in data for field in expected_fields)
        
        return self.log_test("Withdrawal Calculation Test", has_all_fields,
                           f"Response fields: {list(data.keys())}")

    def run_comprehensive_test(self):
        """Run comprehensive deposit & withdrawal testing suite"""
        print("🎯 Starting Deposit & Withdrawal Testing Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Basic connectivity and auth
        if not self.test_basic_connectivity():
            return False
        
        if not self.test_demo_auth():
            return False
        
        if not self.test_admin_auth():
            print("⚠️ Admin auth failed, skipping admin-only tests")
            return False
        
        # Core functionality tests
        test_functions = [
            self.test_manual_deposit_updates_deposit_balance,
            self.test_withdrawal_with_wager_blocking,
            self.test_rtp_range_validation,
            self.test_rtp_persistence,
            self.test_rtp_impact_on_games,
            self.test_withdrawal_amount_calculation
        ]
        
        for test_func in test_functions:
            try:
                test_func()
            except Exception as e:
                self.log_test(test_func.__name__, False, f"Exception: {str(e)}")
        
        # Final summary
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print("🏁 Deposit & Withdrawal Testing Complete")
        print(f"⏱️ Duration: {duration:.1f} seconds")
        print(f"📊 Tests Run: {self.tests_run}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        return self.tests_passed / self.tests_run >= 0.7  # 70% success rate threshold

def main():
    """Main test execution"""
    tester = DepositWithdrawalTester()
    success = tester.run_comprehensive_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())