import requests

def test_create_collection_point():
    # Use the token and secret obtained from the package_register test
    token = "8ea65a03-8bc1-44eb-9392-21ad38502479"
    secret = "c01bfbd2-bd7a-4006-b168-e46debdb5630"

    url = "http://localhost:8080/create-collection-point"
    payload = {
        "secret": secret,
        "token": token
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 200
    yaml_template = response.text
    print(yaml_template)
    assert "version" in yaml_template
    print("Create Collection Point Test Passed")

if __name__ == "__main__":
    test_create_collection_point()
