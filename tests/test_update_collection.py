import requests

def test_update_collection_point():
    url = "http://localhost:8080/update-collection-point"
    payload = {
        "collection_point_id": "cp1",
        "cp_name": "Updated Collection Point",
        "cp_url": "https://updatedcollectionpoint.com",
        "cp_status": "inactive",
        "data_elements": [
            {
                "data_element": "addhar",
                "data_element_title": "Updated Home Address",
                "data_element_description": "Updated description of home address field",
                "data_element_collection_status": "inactive",
                "expiry": "30 days",
                "cross_border": True,
                "data_principal": True,
                "sensitive": False,
                "encrypted": False,
                "retention_period": "1 year",
                "data_owner": "Updated Customer Service Department",
                "legal_basis": "Updated Consent",
                "purposes": [
                    {
                        "purpose_id": "p2",
                        "purpose_description": "Updated purpose description for home address",
                        "purpose_language": "EN"
                    }
                ]
            }
        ]
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 200
    print("Update Collection Point Test Passed")

if __name__ == "__main__":
    test_update_collection_point()
