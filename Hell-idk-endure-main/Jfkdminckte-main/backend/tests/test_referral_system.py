"""
Referral System Tests for EASY MONEY Casino
Tests the full referral cycle:
1. Create referrer and get ref_link
2. Register new user via /api/auth/demo with ref_code
3. Register new user via /api/auth/telegram with ref_code
4. Verify invited_by is saved in new user data
5. Verify referrer stats via /api/ref/stats (referalov should increase)
6. Verify referral bonus after deposit (mock payment)
"""

import pytest
import requests
import os
import random
import string
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://referfix.preview.emergentagent.com').rstrip('/')

class TestReferralSystem:
    """Full referral system E2E tests"""
    
    @pytest.fixture(scope="class")
    def referrer_data(self):
        """Create a referrer user and return their data"""
        # Create unique username for referrer
        username = f"TEST_referrer_{random.randint(100000, 999999)}"
        
        response = requests.post(f"{BASE_URL}/api/auth/demo", json={
            "username": username
        })
        
        assert response.status_code == 200, f"Failed to create referrer: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Referrer creation failed: {data}"
        
        user = data.get("user", {})
        token = data.get("token")
        
        assert "ref_link" in user, "Referrer should have ref_link"
        assert user["ref_link"], "ref_link should not be empty"
        
        print(f"✅ Created referrer: {username}, ref_link: {user['ref_link']}")
        
        return {
            "user": user,
            "token": token,
            "ref_link": user["ref_link"],
            "username": username
        }
    
    def test_01_referrer_has_ref_link(self, referrer_data):
        """Test that referrer has a valid ref_link"""
        ref_link = referrer_data["ref_link"]
        
        assert ref_link is not None, "ref_link should not be None"
        assert len(ref_link) == 10, f"ref_link should be 10 chars (hex), got {len(ref_link)}"
        assert ref_link.isalnum(), "ref_link should be alphanumeric"
        
        print(f"✅ Referrer ref_link is valid: {ref_link}")
    
    def test_02_referrer_initial_stats(self, referrer_data):
        """Test referrer's initial stats (0 referrals)"""
        token = referrer_data["token"]
        
        response = requests.get(
            f"{BASE_URL}/api/ref/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed to get ref stats: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        # Initial stats should be 0
        assert data.get("referalov", -1) == 0, f"Initial referalov should be 0, got {data.get('referalov')}"
        assert data.get("deposited_refs", -1) == 0, f"Initial deposited_refs should be 0"
        
        print(f"✅ Referrer initial stats: referalov=0, deposited_refs=0")
    
    def test_03_register_demo_user_with_ref_code(self, referrer_data):
        """Test registering a new demo user with ref_code"""
        ref_link = referrer_data["ref_link"]
        
        # Create unique username for referred user
        username = f"TEST_referred_demo_{random.randint(100000, 999999)}"
        
        response = requests.post(f"{BASE_URL}/api/auth/demo", json={
            "username": username,
            "ref_code": ref_link
        })
        
        assert response.status_code == 200, f"Failed to register demo user: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Demo registration failed: {data}"
        
        user = data.get("user", {})
        
        # CRITICAL: Verify invited_by is saved
        assert user.get("invited_by") == ref_link, \
            f"invited_by should be '{ref_link}', got '{user.get('invited_by')}'"
        
        print(f"✅ Demo user registered with invited_by={user.get('invited_by')}")
        
        # Store for later tests
        referrer_data["referred_demo_user"] = user
        referrer_data["referred_demo_token"] = data.get("token")
    
    def test_04_referrer_stats_after_demo_registration(self, referrer_data):
        """Test that referrer's referalov increased after demo registration"""
        token = referrer_data["token"]
        
        response = requests.get(
            f"{BASE_URL}/api/ref/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed to get ref stats: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        # referalov should have increased by 1
        assert data.get("referalov", 0) >= 1, \
            f"referalov should be >= 1 after demo registration, got {data.get('referalov')}"
        
        print(f"✅ Referrer stats after demo registration: referalov={data.get('referalov')}")
    
    def test_05_register_telegram_user_with_ref_code(self, referrer_data):
        """Test registering a new Telegram user with ref_code"""
        ref_link = referrer_data["ref_link"]
        
        # Create unique telegram ID
        tg_id = random.randint(100000000, 999999999)
        
        response = requests.post(f"{BASE_URL}/api/auth/telegram", json={
            "id": tg_id,
            "first_name": "TEST_Referred",
            "last_name": "User",
            "username": f"test_tg_user_{tg_id}",
            "ref_code": ref_link
        })
        
        assert response.status_code == 200, f"Failed to register TG user: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"TG registration failed: {data}"
        
        user = data.get("user", {})
        
        # CRITICAL: Verify invited_by is saved
        assert user.get("invited_by") == ref_link, \
            f"invited_by should be '{ref_link}', got '{user.get('invited_by')}'"
        
        print(f"✅ Telegram user registered with invited_by={user.get('invited_by')}")
        
        # Store for later tests
        referrer_data["referred_tg_user"] = user
        referrer_data["referred_tg_token"] = data.get("token")
    
    def test_06_referrer_stats_after_telegram_registration(self, referrer_data):
        """Test that referrer's referalov increased after Telegram registration"""
        token = referrer_data["token"]
        
        response = requests.get(
            f"{BASE_URL}/api/ref/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed to get ref stats: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        # referalov should have increased by 2 (1 demo + 1 telegram)
        assert data.get("referalov", 0) >= 2, \
            f"referalov should be >= 2 after TG registration, got {data.get('referalov')}"
        
        print(f"✅ Referrer stats after TG registration: referalov={data.get('referalov')}")
    
    def test_07_referral_list_shows_referred_users(self, referrer_data):
        """Test that referral list shows the referred users"""
        token = referrer_data["token"]
        
        response = requests.get(
            f"{BASE_URL}/api/ref/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed to get ref list: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        referrals = data.get("referrals", [])
        total_count = data.get("total_count", 0)
        
        assert total_count >= 2, f"total_count should be >= 2, got {total_count}"
        assert len(referrals) >= 2, f"Should have at least 2 referrals in list, got {len(referrals)}"
        
        print(f"✅ Referral list: {len(referrals)} referrals, total_count={total_count}")
    
    def test_08_mock_payment_triggers_ref_bonus(self, referrer_data):
        """Test that mock payment completion triggers referral bonus"""
        # Get referred user's token (use TG user as they're not demo)
        referred_token = referrer_data.get("referred_tg_token")
        referrer_token = referrer_data["token"]
        
        if not referred_token:
            pytest.skip("No referred TG user token available")
        
        # Get referrer's initial income
        response = requests.get(
            f"{BASE_URL}/api/ref/stats",
            headers={"Authorization": f"Bearer {referrer_token}"}
        )
        initial_income = response.json().get("income", 0)
        initial_deposited_refs = response.json().get("deposited_refs", 0)
        
        # Create a mock payment for the referred user
        response = requests.post(
            f"{BASE_URL}/api/payment/create",
            headers={"Authorization": f"Bearer {referred_token}"},
            json={
                "amount": 500,
                "provider": "1plat",
                "method": "sbp"
            }
        )
        
        # Payment creation might fail if provider not configured, that's OK
        if response.status_code != 200:
            print(f"⚠️ Payment creation failed (expected if provider not configured): {response.text}")
            pytest.skip("Payment provider not configured")
        
        data = response.json()
        if not data.get("success"):
            pytest.skip(f"Payment creation failed: {data}")
        
        payment_id = data.get("payment_id")
        if not payment_id:
            pytest.skip("No payment_id returned")
        
        # Complete the mock payment
        response = requests.post(
            f"{BASE_URL}/api/payment/mock/complete/{payment_id}",
            headers={"Authorization": f"Bearer {referred_token}"}
        )
        
        if response.status_code != 200:
            print(f"⚠️ Mock payment completion failed: {response.text}")
            pytest.skip("Mock payment completion not available")
        
        data = response.json()
        if not data.get("success"):
            pytest.skip(f"Mock payment completion failed: {data}")
        
        # Wait a bit for async processing
        time.sleep(1)
        
        # Check referrer's income increased
        response = requests.get(
            f"{BASE_URL}/api/ref/stats",
            headers={"Authorization": f"Bearer {referrer_token}"}
        )
        
        new_income = response.json().get("income", 0)
        new_deposited_refs = response.json().get("deposited_refs", 0)
        
        # Income should have increased (10% of 500 = 50)
        assert new_income > initial_income, \
            f"Referrer income should increase after deposit. Initial: {initial_income}, New: {new_income}"
        
        # deposited_refs should have increased
        assert new_deposited_refs > initial_deposited_refs, \
            f"deposited_refs should increase. Initial: {initial_deposited_refs}, New: {new_deposited_refs}"
        
        print(f"✅ Referral bonus working: income {initial_income} -> {new_income}")


class TestReferralEdgeCases:
    """Edge case tests for referral system"""
    
    def test_invalid_ref_code_ignored(self):
        """Test that invalid ref_code doesn't break registration"""
        username = f"TEST_invalid_ref_{random.randint(100000, 999999)}"
        
        response = requests.post(f"{BASE_URL}/api/auth/demo", json={
            "username": username,
            "ref_code": "invalid_code_12345"
        })
        
        assert response.status_code == 200, f"Registration should succeed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        user = data.get("user", {})
        # invited_by should be None for invalid ref_code
        assert user.get("invited_by") is None, \
            f"invited_by should be None for invalid ref_code, got {user.get('invited_by')}"
        
        print(f"✅ Invalid ref_code handled correctly (invited_by=None)")
    
    def test_empty_ref_code_ignored(self):
        """Test that empty ref_code doesn't break registration"""
        username = f"TEST_empty_ref_{random.randint(100000, 999999)}"
        
        response = requests.post(f"{BASE_URL}/api/auth/demo", json={
            "username": username,
            "ref_code": ""
        })
        
        assert response.status_code == 200, f"Registration should succeed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        user = data.get("user", {})
        assert user.get("invited_by") is None, \
            f"invited_by should be None for empty ref_code"
        
        print(f"✅ Empty ref_code handled correctly")
    
    def test_no_ref_code_works(self):
        """Test that registration without ref_code works"""
        username = f"TEST_no_ref_{random.randint(100000, 999999)}"
        
        response = requests.post(f"{BASE_URL}/api/auth/demo", json={
            "username": username
        })
        
        assert response.status_code == 200, f"Registration should succeed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        user = data.get("user", {})
        assert user.get("invited_by") is None, \
            f"invited_by should be None when no ref_code provided"
        
        print(f"✅ Registration without ref_code works correctly")


class TestReferralStats:
    """Tests for referral statistics endpoints"""
    
    def test_ref_stats_requires_auth(self):
        """Test that /api/ref/stats requires authentication"""
        response = requests.get(f"{BASE_URL}/api/ref/stats")
        
        assert response.status_code == 401, \
            f"Should return 401 without auth, got {response.status_code}"
        
        print(f"✅ /api/ref/stats requires authentication")
    
    def test_ref_list_requires_auth(self):
        """Test that /api/ref/list requires authentication"""
        response = requests.get(f"{BASE_URL}/api/ref/list")
        
        assert response.status_code == 401, \
            f"Should return 401 without auth, got {response.status_code}"
        
        print(f"✅ /api/ref/list requires authentication")
    
    def test_ref_stats_returns_correct_structure(self):
        """Test that ref stats returns correct data structure"""
        # Create a test user
        username = f"TEST_stats_struct_{random.randint(100000, 999999)}"
        
        response = requests.post(f"{BASE_URL}/api/auth/demo", json={
            "username": username
        })
        
        token = response.json().get("token")
        
        response = requests.get(
            f"{BASE_URL}/api/ref/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "success" in data
        assert "ref_link" in data
        assert "referalov" in data
        assert "deposited_refs" in data
        assert "income" in data
        assert "income_all" in data
        assert "level" in data  # Contains current level info
        assert "levels" in data  # Contains all levels
        
        print(f"✅ Ref stats structure is correct: {list(data.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
