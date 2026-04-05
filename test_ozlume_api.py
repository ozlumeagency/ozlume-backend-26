"""
OZlume Agency Website - Backend API Tests
Tests for contact form submission and basic API endpoints
"""
import pytest
import requests
import os


class TestHealthEndpoints:
    """Basic API health and root endpoint tests"""
    
    def test_root_endpoint(self):
        """Test root API endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Root endpoint working: {data}")
    
    def test_status_get_endpoint(self):
        """Test GET /api/status endpoint"""
        response = requests.get(f"{BASE_URL}/api/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Status GET endpoint working, returned {len(data)} items")


class TestContactForm:
    """Contact form submission tests"""
    
    def test_contact_form_valid_submission(self):
        """Test valid contact form submission"""
        payload = {
            "name": "TEST_John Doe",
            "email": "test@example.com",
            "whatsapp": "+61 400 000 000",
            "company": "Test Company",
            "message": "This is a test message from automated testing."
        }
        response = requests.post(f"{BASE_URL}/api/contact", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        assert "message" in data
        print(f"✓ Contact form submission successful: {data}")
    
    def test_contact_form_without_company(self):
        """Test contact form submission without optional company field"""
        payload = {
            "name": "TEST_Jane Smith",
            "email": "jane@example.com",
            "whatsapp": "+61 400 111 222",
            "message": "Test message without company field."
        }
        response = requests.post(f"{BASE_URL}/api/contact", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        print(f"✓ Contact form without company field successful: {data}")
    
    def test_contact_form_missing_required_fields(self):
        """Test contact form with missing required fields returns error"""
        payload = {
            "name": "TEST_Missing Fields"
            # Missing email, whatsapp, message
        }
        response = requests.post(f"{BASE_URL}/api/contact", json=payload)
        # Should return 422 for validation error
        assert response.status_code == 422
        print(f"✓ Contact form correctly rejects missing fields: {response.status_code}")
    
    def test_contact_form_invalid_email(self):
        """Test contact form with invalid email format"""
        payload = {
            "name": "TEST_Invalid Email",
            "email": "not-an-email",
            "whatsapp": "+61 400 000 000",
            "message": "Test message with invalid email."
        }
        response = requests.post(f"{BASE_URL}/api/contact", json=payload)
        # Should return 422 for validation error
        assert response.status_code == 422
        print(f"✓ Contact form correctly rejects invalid email: {response.status_code}")


class TestStatusEndpoint:
    """Status endpoint CRUD tests"""
    
    def test_create_status_check(self):
        """Test creating a status check"""
        payload = {
            "client_name": "TEST_Automated_Test_Client"
        }
        response = requests.post(f"{BASE_URL}/api/status", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["client_name"] == "TEST_Automated_Test_Client"
        assert "timestamp" in data
        print(f"✓ Status check created: {data['id']}")
        return data["id"]
    
    def test_get_status_checks_after_create(self):
        """Test retrieving status checks after creation"""
        # First create one
        payload = {"client_name": "TEST_Verify_Get"}
        requests.post(f"{BASE_URL}/api/status", json=payload)
        
        # Then get all
        response = requests.get(f"{BASE_URL}/api/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify our test entry exists
        test_entries = [d for d in data if "TEST_" in d.get("client_name", "")]
        assert len(test_entries) > 0
        print(f"✓ Status checks retrieved, found {len(test_entries)} test entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
