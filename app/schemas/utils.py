import requests
from app.config.db import *
from bson import ObjectId

def save_data_to_concur(org_id: str, payload: dict):
    url = f"https://concur.adnan-qasim.me/data-element/post/{org_id}"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raises an error for 4xx/5xx responses
        return response.json()  # Returns the response as JSON
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {str(e)}")
        return None


def get_collection_point_with_translations(cp_id, org_id, app_id):
    # Fetch the collection point data
    collection_point = collection_point_collection.find_one(
        {"_id": ObjectId(cp_id), "org_id": org_id, "application_id": app_id}
    )

    if collection_point:
        # Loop through the data elements and purposes to fetch translations
        for data_element in collection_point.get("data_elements", []):
            for purpose in data_element.get("purposes", []):
                translated_purpose_id = purpose.get("translated_purpose_id")
                if translated_purpose_id:
                    # Fetch the translation details
                    translation = consent_directory_collection.find_one(
                        {"_id": ObjectId(translated_purpose_id)}
                    )
                    if translation:
                        # Update the purpose with the translation data
                        purpose["translations"] = translation["purpose"]

        # Create the notice_info dictionary (example structure)
        notice_info = {
            "cp_name": collection_point.get("cp_name"),
            "cp_status": collection_point.get("cp_status"),
            "purposes": collection_point.get("data_elements", []),
        }

        return notice_info

    return None

def update_contract_status_for_all():

    # Fetch all documents in the collection
    cps = collection_point.find({})

    headers = {"x-token": "string"}  # Replace with actual token if required

    # Iterate over each document
    for cp in cps:
        # Check if cp_contract_id exists in the document
        if "cp_contract_id" not in cp:
            print(f"cp_contract_id not found for document with _id: {cp['_id']}")
            continue

        cp_contract_id = cp["cp_contract_id"]
        url = f"http://127.0.0.1:8000/get-cp-status/{cp_contract_id}"

        try:
            # Make a GET request to check the contract status
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            response_data = response.json()

            # Check if the blockchain_status is 'deployed'
            if response_data.get("blockchain_status") == "deployed":
                txn_hash = response_data.get("txn_hash")
                contract_address = response_data.get("contract_address")

                # Update the document with txn_hash and contract_address
                collection.update_one(
                    {"_id": document["_id"]},
                    {
                        "$set": {
                            "txn_hash": txn_hash,
                            "contract_address": contract_address
                        }
                    }
                )
                print(f"Updated document with _id: {document['_id']}")

            else:
                print(f"Contract not deployed for document with _id: {document['_id']}")

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while checking contract status for _id: {document['_id']} - {str(e)}")
