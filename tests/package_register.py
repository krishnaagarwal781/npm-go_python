import requests


url = "http://localhost:8080/package-register"
payload = {
    "developer_email": "test@example.com",
    "developer_website": "https://example.com",
    "developer_city": "Sample City",
    "developer_mobile": "1234567890",
    "organisation_name": "Example Org",
}
response = requests.post(url, json=payload)
assert response.status_code == 200
data = response.json()
assert "secret" in data
assert "token" in data
print("Package Register Test Passed")
