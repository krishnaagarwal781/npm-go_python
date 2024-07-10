import requests

def test_post_collection_point():
    url = "http://localhost:8080/post-collection-point"
    payload = {
        "collection_point_id": "cp1",
        "cp_name": "Collection Point 1",
        "cp_url": "https://collectionpoint1.com",
        "cp_status": "active",
        "data_elements": [
            {
                "data_element": "home_address",
                "data_element_title": "Home Address",
                "data_element_description": "One line description of home address field",
                "data_element_collection_status": "active",
                "expiry": "90 days",
                "cross_border": False,
                "data_principal": False,
                "sensitive": True,
                "encrypted": True,
                "retention_period": "5 years",
                "data_owner": "Customer Service Department",
                "legal_basis": "Consent",
                "purposes": [
                    {
                        "purpose_id": "p1",
                        "purpose_description": "Purpose description for home address",
                        "purpose_language": "EN"
                    }
                ]
            }
        ]
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 200
    print("Post Collection Point Test Passed")

if __name__ == "__main__":
    test_post_collection_point()
