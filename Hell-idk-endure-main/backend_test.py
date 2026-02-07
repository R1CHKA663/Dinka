#!/usr/bin/env python3
"""
EASY MONEY Platform Comprehensive Testing
Testing RTP functionality across all games, admin controls, deposits, and promo codes
"""

import requests
import json
import sys
import time
from datetime import datetime

class EasyMoneyTester:
    def __init__(self, base_url="https://total-launch.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_token = None
        self.user_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []

    def log_result(self, test_name, success, details="", expected="", actual=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "details": details,
            "expected": expected,
            "actual": actual,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        print(f"{status} - {test_name}")
        if details:
            print(f"    {details}")
        if not success and expected:
            print(f"    Expected: {expected}")
            print(f"    Actual: {actual}")

    def make_request(self, method, endpoint, data=None, headers=None, token=None):
        """Make HTTP request with error handling"""
        url = f"{self.api_url}{endpoint}"
        req_headers = {'Content-Type': 'application/json'}
        
        if token:
            req_headers['Authorization'] = f'Bearer {token}'
        if headers:
            req_headers.update(headers)
            
        try:
            if method == 'GET':
                response = requests.get(url, headers=req_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=req_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=req_headers, timeout=30)
            
            return response
        except Exception as e:
            print(f"Request error: {e}")
            return None

    def test_admin_login(self):
        """Test admin authentication"""
        print("\n🔐 Testing Admin Authentication...")
        
        # Admin login
        response = self.make_request('POST', '/admin/login', {
            'password': 'ADMIn1@tim'
        })
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('token'):
                self.admin_token = data['token']
                self.log_result("Admin Login", True, f"Admin authenticated successfully")
                return True
            else:
                self.log_result("Admin Login", False, f"Login failed: {data.get('error', 'Unknown error')}")
        else:
            self.log_result("Admin Login", False, f"HTTP {response.status_code if response else 'No response'}")
        
        return False

    def test_demo_user_creation(self):
        """Create demo user for testing"""
        print("\n👤 Creating Demo User...")
        
        username = f"test_user_{int(time.time())}"
        response = self.make_request('POST', '/auth/demo', {
            'username': username
        })
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('token'):
                self.user_token = data['token']
                self.user_id = data['user']['id']
                self.log_result("Demo User Creation", True, f"User created: {username}")
                return True
            else:
                self.log_result("Demo User Creation", False, f"Creation failed: {data.get('error', 'Unknown error')}")
        else:
            self.log_result("Demo User Creation", False, f"HTTP {response.status_code if response else 'No response'}")
        
        return False

    def test_rtp_validation(self):
        """Test RTP range validation (10-99.9%)"""
        print("\n🎯 Testing RTP Validation...")
        
        if not self.admin_token:
            self.log_result("RTP Validation", False, "No admin token available")
            return False
        
        # Test invalid RTP values
        invalid_values = [0, 5, 100, 150, -10]
        valid_values = [10, 50, 95, 99.9]
        
        for rtp in invalid_values:
            response = self.make_request('PUT', '/admin/settings', {
                'dice_rtp': rtp
            }, token=self.admin_token)
            
            if response and response.status_code == 400:
                self.log_result(f"RTP Validation - Invalid {rtp}%", True, f"Correctly rejected RTP {rtp}%")
            else:
                self.log_result(f"RTP Validation - Invalid {rtp}%", False, f"Should reject RTP {rtp}% but didn't")
        
        # Test valid RTP values
        for rtp in valid_values:
            response = self.make_request('PUT', '/admin/settings', {
                'dice_rtp': rtp
            }, token=self.admin_token)
            
            if response and response.status_code == 200:
                self.log_result(f"RTP Validation - Valid {rtp}%", True, f"Correctly accepted RTP {rtp}%")
            else:
                self.log_result(f"RTP Validation - Valid {rtp}%", False, f"Should accept RTP {rtp}% but didn't")

    def test_rtp_settings_persistence(self):
        """Test RTP settings are saved and retrieved correctly"""
        print("\n💾 Testing RTP Settings Persistence...")
        
        if not self.admin_token:
            self.log_result("RTP Settings Persistence", False, "No admin token available")
            return False
        
        # Set specific RTP values for all games
        test_rtps = {
            'dice_rtp': 85.5,
            'mines_rtp': 90.0,
            'tower_rtp': 88.5,
            'bubbles_rtp': 92.0,
            'crash_rtp': 87.0,
            'x100_rtp': 89.5
        }
        
        # Set RTP values
        response = self.make_request('PUT', '/admin/settings', test_rtps, token=self.admin_token)
        
        if not response or response.status_code != 200:
            self.log_result("RTP Settings Save", False, f"Failed to save RTP settings")
            return False
        
        # Retrieve and verify
        response = self.make_request('GET', '/admin/settings', token=self.admin_token)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get('success'):
                settings = data.get('settings', {})
                all_correct = True
                
                for key, expected_value in test_rtps.items():
                    actual_value = settings.get(key)
                    if actual_value != expected_value:
                        self.log_result(f"RTP Persistence - {key}", False, 
                                      f"Expected {expected_value}, got {actual_value}")
                        all_correct = False
                    else:
                        self.log_result(f"RTP Persistence - {key}", True, 
                                      f"Correctly saved and retrieved {expected_value}")
                
                return all_correct
            else:
                self.log_result("RTP Settings Retrieve", False, "Failed to retrieve settings")
        else:
            self.log_result("RTP Settings Retrieve", False, f"HTTP {response.status_code if response else 'No response'}")
        
        return False

    def test_game_rtp_impact(self, game_name, endpoint, bet_data, rtp_key):
        """Test RTP impact on specific game"""
        print(f"\n🎲 Testing {game_name} RTP Impact...")
        
        if not self.admin_token or not self.user_token:
            self.log_result(f"{game_name} RTP Test", False, "Missing tokens")
            return False
        
        # Test with low RTP (20%)
        low_rtp = 20
        response = self.make_request('PUT', '/admin/settings', {rtp_key: low_rtp}, token=self.admin_token)
        if not response or response.status_code != 200:
            self.log_result(f"{game_name} Low RTP Set", False, "Failed to set low RTP")
            return False
        
        # Play multiple rounds with low RTP
        low_rtp_wins = 0
        rounds = 20
        
        for i in range(rounds):
            response = self.make_request('POST', endpoint, bet_data, token=self.user_token)
            if response and response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Check for win based on game type
                    if game_name == 'Dice':
                        if data.get('win', 0) > 0:
                            low_rtp_wins += 1
                    elif game_name == 'Bubbles':
                        if data.get('status') == 'win':
                            low_rtp_wins += 1
                    # Add other game types as needed
            time.sleep(0.1)  # Small delay between requests
        
        low_win_rate = (low_rtp_wins / rounds) * 100
        
        # Test with high RTP (95%)
        high_rtp = 95
        response = self.make_request('PUT', '/admin/settings', {rtp_key: high_rtp}, token=self.admin_token)
        if not response or response.status_code != 200:
            self.log_result(f"{game_name} High RTP Set", False, "Failed to set high RTP")
            return False
        
        # Play multiple rounds with high RTP
        high_rtp_wins = 0
        
        for i in range(rounds):
            response = self.make_request('POST', endpoint, bet_data, token=self.user_token)
            if response and response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Check for win based on game type
                    if game_name == 'Dice':
                        if data.get('win', 0) > 0:
                            high_rtp_wins += 1
                    elif game_name == 'Bubbles':
                        if data.get('status') == 'win':
                            high_rtp_wins += 1
                    # Add other game types as needed
            time.sleep(0.1)
        
        high_win_rate = (high_rtp_wins / rounds) * 100
        
        # Verify RTP impact
        if high_win_rate > low_win_rate:
            self.log_result(f"{game_name} RTP Impact", True, 
                          f"Low RTP: {low_win_rate}% wins, High RTP: {high_win_rate}% wins")
            return True
        else:
            self.log_result(f"{game_name} RTP Impact", False, 
                          f"Expected high RTP to have more wins. Low: {low_win_rate}%, High: {high_win_rate}%")
            return False

    def test_crash_rtp_formula(self):
        """Test Crash game RTP formula and synchronization"""
        print("\n🚀 Testing Crash RTP Formula...")
        
        if not self.admin_token or not self.user_token:
            self.log_result("Crash RTP Test", False, "Missing tokens")
            return False
        
        # Set specific RTP for crash
        crash_rtp = 80  # Lower RTP should mean more crashes at low multipliers
        response = self.make_request('PUT', '/admin/settings', {'crash_rtp': crash_rtp}, token=self.admin_token)
        
        if not response or response.status_code != 200:
            self.log_result("Crash RTP Set", False, "Failed to set crash RTP")
            return False
        
        # Test crash betting and cashout
        crash_points = []
        successful_cashouts = 0
        rounds = 10
        
        for i in range(rounds):
            # Place bet
            bet_response = self.make_request('POST', '/games/crash/bet', {'bet': 10}, token=self.user_token)
            
            if bet_response and bet_response.status_code == 200:
                bet_data = bet_response.json()
                if bet_data.get('success'):
                    bet_id = bet_data.get('bet_id')
                    
                    # Try to cashout at 2x
                    time.sleep(0.5)  # Wait a bit
                    cashout_response = self.make_request('POST', f'/games/crash/cashout/{bet_id}', 
                                                       {'multiplier': 2.0}, token=self.user_token)
                    
                    if cashout_response and cashout_response.status_code == 200:
                        cashout_data = cashout_response.json()
                        if cashout_data.get('success'):
                            successful_cashouts += 1
                    
                    # Check status to get crash point
                    status_response = self.make_request('GET', f'/games/crash/status/{bet_id}?current_mult=10', 
                                                      token=self.user_token)
                    if status_response and status_response.status_code == 200:
                        status_data = status_response.json()
                        # Crash point would be revealed in the bet data after game ends
            
            time.sleep(0.2)
        
        cashout_rate = (successful_cashouts / rounds) * 100
        
        # With 80% RTP, we expect fewer successful cashouts at 2x
        if cashout_rate < 50:  # Expecting low success rate with low RTP
            self.log_result("Crash RTP Formula", True, 
                          f"Low RTP ({crash_rtp}%) resulted in {cashout_rate}% successful cashouts at 2x")
            return True
        else:
            self.log_result("Crash RTP Formula", False, 
                          f"Expected low cashout rate with {crash_rtp}% RTP, got {cashout_rate}%")
            return False

    def test_manual_deposit(self):
        """Test manual deposit functionality"""
        print("\n💰 Testing Manual Deposit...")
        
        if not self.admin_token or not self.user_id:
            self.log_result("Manual Deposit", False, "Missing admin token or user ID")
            return False
        
        # Get initial balance
        user_response = self.make_request('GET', '/auth/me', token=self.user_token)
        if not user_response or user_response.status_code != 200:
            self.log_result("Manual Deposit - Get Initial Balance", False, "Failed to get user balance")
            return False
        
        initial_balance = user_response.json()['user']['deposit_balance']
        
        # Make manual deposit
        deposit_amount = 100
        deposit_response = self.make_request('POST', '/admin/manual-deposit', {
            'user_id': self.user_id,
            'amount': deposit_amount
        }, token=self.admin_token)
        
        if not deposit_response or deposit_response.status_code != 200:
            self.log_result("Manual Deposit - Execute", False, "Failed to execute manual deposit")
            return False
        
        # Verify balance update
        user_response = self.make_request('GET', '/auth/me', token=self.user_token)
        if user_response and user_response.status_code == 200:
            new_balance = user_response.json()['user']['deposit_balance']
            expected_balance = initial_balance + deposit_amount
            
            if abs(new_balance - expected_balance) < 0.01:
                self.log_result("Manual Deposit", True, 
                              f"Balance updated correctly: {initial_balance} → {new_balance}")
                return True
            else:
                self.log_result("Manual Deposit", False, 
                              f"Balance incorrect. Expected: {expected_balance}, Got: {new_balance}")
        else:
            self.log_result("Manual Deposit - Verify Balance", False, "Failed to verify balance update")
        
        return False

    def test_promo_code_system(self):
        """Test promo code activation and wager system"""
        print("\n🎁 Testing Promo Code System...")
        
        if not self.admin_token or not self.user_id:
            self.log_result("Promo Code System", False, "Missing tokens")
            return False
        
        # Create a promo code
        promo_data = {
            'code': f'TEST{int(time.time())}',
            'amount': 50,
            'wager': 100,
            'uses': 1
        }
        
        create_response = self.make_request('POST', '/admin/promo', promo_data, token=self.admin_token)
        
        if not create_response or create_response.status_code != 200:
            self.log_result("Promo Code Creation", False, "Failed to create promo code")
            return False
        
        # Activate promo code
        activate_response = self.make_request('POST', '/promo/activate', {
            'code': promo_data['code']
        }, token=self.user_token)
        
        if not activate_response or activate_response.status_code != 200:
            self.log_result("Promo Code Activation", False, "Failed to activate promo code")
            return False
        
        # Verify promo balance and wager
        user_response = self.make_request('GET', '/auth/me', token=self.user_token)
        if user_response and user_response.status_code == 200:
            user_data = user_response.json()['user']
            promo_balance = user_data.get('promo_balance', 0)
            wager = user_data.get('wager', 0)
            
            if promo_balance >= promo_data['amount'] and wager >= promo_data['wager']:
                self.log_result("Promo Code System", True, 
                              f"Promo activated: +{promo_balance}₽ promo, {wager}₽ wager")
                return True
            else:
                self.log_result("Promo Code System", False, 
                              f"Incorrect values. Promo: {promo_balance}, Wager: {wager}")
        else:
            self.log_result("Promo Code Verification", False, "Failed to verify promo activation")
        
        return False

    def test_wager_blocking_system(self):
        """Test that wager blocks only promo_balance, not deposit_balance"""
        print("\n🔒 Testing Wager Blocking System...")
        
        if not self.user_token:
            self.log_result("Wager Blocking System", False, "No user token")
            return False
        
        # Check withdrawal info with active wager
        withdraw_response = self.make_request('GET', '/withdraw/info', token=self.user_token)
        
        if withdraw_response and withdraw_response.status_code == 200:
            data = withdraw_response.json()
            if data.get('success'):
                withdrawable = data.get('withdrawable', {})
                from_deposit = withdrawable.get('from_deposit', 0)
                from_promo = withdrawable.get('from_promo', 0)
                locked_promo = withdrawable.get('locked_promo', 0)
                
                # With active wager, deposit should be withdrawable but promo should be limited
                if from_deposit > 0 and (from_promo == 0 or locked_promo > 0):
                    self.log_result("Wager Blocking System", True, 
                                  f"Wager correctly blocks promo ({locked_promo}₽ locked) but allows deposit withdrawal ({from_deposit}₽)")
                    return True
                else:
                    self.log_result("Wager Blocking System", False, 
                                  f"Incorrect blocking. Deposit: {from_deposit}₽, Promo: {from_promo}₽, Locked: {locked_promo}₽")
            else:
                self.log_result("Wager Blocking System", False, "Failed to get withdrawal info")
        else:
            self.log_result("Wager Blocking System", False, f"HTTP {withdraw_response.status_code if withdraw_response else 'No response'}")
        
        return False

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting EASY MONEY Platform Comprehensive Testing")
        print("=" * 60)
        
        # Authentication tests
        if not self.test_admin_login():
            print("❌ Admin login failed - skipping admin tests")
        
        if not self.test_demo_user_creation():
            print("❌ Demo user creation failed - skipping user tests")
            return
        
        # RTP validation and settings tests
        self.test_rtp_validation()
        self.test_rtp_settings_persistence()
        
        # Game RTP impact tests
        self.test_game_rtp_impact("Dice", "/games/dice/play", 
                                 {"bet": 10, "chance": 50, "type": "under"}, "dice_rtp")
        
        self.test_game_rtp_impact("Bubbles", "/games/bubbles/play", 
                                 {"bet": 10, "target": 2.0}, "bubbles_rtp")
        
        # Crash specific test
        self.test_crash_rtp_formula()
        
        # Deposit and withdrawal tests
        self.test_manual_deposit()
        
        # Promo code and wager tests
        self.test_promo_code_system()
        self.test_wager_blocking_system()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Print failed tests
        failed_tests = [r for r in self.results if not r['success']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        return self.tests_passed / self.tests_run if self.tests_run > 0 else 0

if __name__ == "__main__":
    tester = EasyMoneyTester()
    success_rate = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success_rate >= 0.8 else 1)