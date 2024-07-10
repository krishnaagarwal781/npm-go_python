import requests

def test_get_collection_points():
    url = "http://localhost:8080/get-collection-points"
    response = requests.get(url)
    assert response.status_code == 200
    collection_points = response.json()
    assert isinstance(collection_points, list)
    print("Get Collection Points Test Passed")

if __name__ == "__main__":
    test_get_collection_points()
