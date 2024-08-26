from fastapi import FastAPI, HTTPException, Header, APIRouter, Request, Query
from fastapi.responses import JSONResponse
from bson import ObjectId
from datetime import datetime, timedelta
from app.config.db import (
    consent_preferences_collection,
    collection_point_collection,
    developer_details_collection,
    user_consent_headers,
)
from app.models.models import *
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from limits.storage import RedisStorage
import hashlib
import json
from typing import Dict, Any
from uuid import uuid4
from collections import defaultdict
from pymongo.errors import WriteError

#Abhishek Redis Connection
import redis
import json


consentRouter = APIRouter()

#Abhishek Redis Connection
r = redis.Redis(
  host='redis-12042.c212.ap-south-1-1.ec2.redns.redis-cloud.com',
  port=12042,
  password='XPArYXZ1ENkQyQv31JoRpjnqnV49rvjD')


# Initialize RedisStorage and Limiter
redis_url = "redis://default:GtOhsmeCwPJsZC8B0A8R2ihcA7pDVXem@redis-11722.c44.us-east-1-2.ec2.cloud.redislabs.com:11722/0"  # Adjust the Redis URL as needed
storage = RedisStorage(redis_url)
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)


def generate_body_hash(body: Dict[str, Any]) -> str:
    body_json = json.dumps(body, sort_keys=True).encode("utf-8")
    hash_object = hashlib.sha256(body_json)
    return hash_object.hexdigest()


def harsh_blockchain_functionationing(consent_document: Dict[str, Any]) -> str:
    return str(uuid4())


def calculate_future_date(base_date: datetime, days: int) -> str:
    future_date = base_date + timedelta(days=days)
    return future_date.isoformat()


@consentRouter.post("/post-consent-preference", tags=["Consent Preference"])
@limiter.limit("5/minute")
async def post_consent_preference(
    request: Request,
    data: ConsentPreferenceBody,
    dp_id: str,
    df_id: str = Header(...),
    application_id: str = Header(...),
    cp_id: str = Header(...),
    dp_e: Optional[str] = Header(...),
):
    # Step 1: Validate the collection point and retrieve data elements
    collection_point = collection_point_collection.find_one(
        {"_id": ObjectId(cp_id), "application_id": application_id}
    )
    if not collection_point:
        raise HTTPException(status_code=404, detail="Collection point not found")

    print(collection_point)
    # Step 2: Validate the provided data elements against the collection point's data elements
    data_elements_ids = {
        element["data_element"] for element in collection_point.get("data_elements", [])
    }
    for element in data.data_elements:
        if element.data_element not in data_elements_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data_element: {element.data_element}",
            )

    # Step 3: Aggregate consents by data_element
    consent_scope = {}
    for element in data.data_elements:
        if element.data_element not in consent_scope:
            consent_scope[element.data_element] = {
                "data_element": element.data_element,
                "consents": [],
            }

        # Find the matching data element in the collection point
        collection_point_element = next(
            (
                el
                for el in collection_point["data_elements"]
                if el["data_element"] == element.data_element
            ),
            None,
        )

        if not collection_point_element:
            continue
        for consent in element.consents:
            # Retrieve purpose details from the collection point
            purpose_details = next(
                (
                    purpose
                    for purpose in collection_point_element["purposes"]
                    if purpose["purpose_id"] == consent.purpose_id
                ),
                {},
            )

            # Calculate purpose_expiry and purpose_retention
            purpose_expiry_days = purpose_details.get("purpose_expiry")
            purpose_retention_days = purpose_details.get("purpose_retention")
            print(purpose_expiry_days)
            print(purpose_retention_days)

            consent_scope[element.data_element]["consents"].append(
                {
                    "purpose_id": consent.purpose_id,
                    "consent_status": consent.consent_status,
                    "purpose_shared": consent.shared,
                    "data_processors": consent.data_processors,
                    "purpose_cross_border": purpose_details.get(
                        "purpose_cross_border", False
                    ),
                    "purpose_mandatory": purpose_details.get(
                        "purpose_mandatory", False
                    ),
                    "purpose_legal": purpose_details.get("purpose_legal", False),
                    "purpose_revokable": purpose_details.get(
                        "purpose_revokable", False
                    ),
                    "purpose_encrypted": purpose_details.get(
                        "purpose_encrypted", False
                    ),
                    "purpose_expiry": calculate_future_date(
                        datetime.utcnow(), purpose_expiry_days
                    ),
                    "purpose_retention": calculate_future_date(
                        datetime.utcnow(), purpose_retention_days
                    ),
                    "consent_timestamp": consent.consent_timestamp,
                }
            )

    # Convert the aggregated consent_scope to a list
    consent_scope_list = list(consent_scope.values())

    # Step 4: Build the consent document
    consent_document = {
        "consent": {
            "context": "https://consent.foundation/artifact/v1",
            "cp_name": collection_point.get("cp_name", ""),
            "agreement_hash_id": "",  # Placeholder to be updated
            "linked_agreement": data.linked_agreement,
            "data_principal": {
                "dp_id": dp_id,
                "dp_e": dp_e,
            },
            "data_fiduciary": {
                "df_id": df_id,
                "agreement_date": datetime.utcnow().isoformat(),
                "date_of_consent": datetime.utcnow().isoformat(),
                "revocation_date": None,
            },
            "consent_language": data.consent_language,
            "consent_scope": consent_scope_list,
            "timestamp": datetime.utcnow().isoformat(),
            "agreement_id": "",  # Placeholder to be updated
        },
    }

    # Step 5: Generate and assign the consent document hash
    consent_hash = generate_body_hash(consent_document)
    consent_document["consent"]["agreement_hash_id"] = consent_hash

    # Step 6: Store the request headers and body in user_consent_headers collection
    body_hash = generate_body_hash(data.dict())
    user_consent_document = {
        "headers": dict(request.headers),
        "body": data.dict(),
        "body_hash": body_hash,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Step 7: Insert user consent document and retrieve the inserted ID
        user_consent_result = user_consent_headers.insert_one(user_consent_document)
        user_consent_id = user_consent_result.inserted_id

        # Step 8: Interact with blockchain service to get agreement ID
        agreement_id = harsh_blockchain_functionationing(consent_document)
        consent_document["consent"]["agreement_id"] = agreement_id

        # Step 9: Upsert the consent document in MongoDB
        consent_preferences_collection.update_one(
            {"df_id": df_id, "app_id": application_id, "cp_id": cp_id, "dp_id": dp_id},
            {
                "$set": {
                    "consent_document": consent_document,
                    "user_consent_request_id": str(user_consent_id),
                    "is_active_consent_preference": True,
                }
            },
            upsert=True,
        )


        #updating the redis cache after posting the consent
        cache_key = f"consent_preferences:{dp_id}:{df_id}"

        # Transform the consent document into the format expected by get_preferences
        consent_scope_list = consent_document.get("consent", {}).get("consent_scope", [])
        grouped_result = defaultdict(list)

        for scope in consent_scope_list:
            data_element_key = scope.get("data_element")
            for consent in scope.get("consents", []):
                consent_data = {
                    "cp_id": cp_id,
                    "cp_name": consent_document["consent"].get("cp_name", ""),
                    "de_name": data_element_key,  # Using the data element key as a placeholder for title
                    "description": {
                        "activity": "",  # Placeholder, can be enhanced with actual data
                        "consent": consent.get("consent_timestamp", ""),
                        "validTill": consent.get("purpose_expiry", ""),
                        "agreement": consent_document["consent"].get("agreement_id", ""),
                        "retentionTill": consent.get("purpose_retention", ""),
                        "consent_status": consent.get("consent_status", ""),
                        "consent_id": consent.get("purpose_id"),
                        "revokedDate": consent.get("revoked_date", ""),
                        "purpose_mandatory": consent.get("purpose_mandatory", {}),
                        "purpose_legal": consent.get("purpose_legal", {}),
                        "purpose_revokable": consent.get("purpose_revokable", False),
                        "purpose_shared": consent.get("purpose_shared", False),
                    },
                }
                grouped_result[data_element_key].append(consent_data)
        
        result = {name: consents for name, consents in grouped_result.items()}
        
        # Store the result in Redis with a 1-hour expiration time
        r.set(cache_key, json.dumps(result), ex=3600)


        # Step 10: Return the response with the consent artifact and its hash
        return JSONResponse(
            content={
                "message": "Consent preferences updated successfully",
                "agreement_id": agreement_id,
                "consent_artifact": consent_document,
                "consent_artifact_hash": consent_hash,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@consentRouter.get("/get-preferences", tags=["Consent Preference"])
async def get_preferences(
    dp_id: str = Query(..., description="Data Principal ID"),
    df_id: str = Query(..., description="Data Fiduciary ID"),
) -> Dict[str, List[Dict]]:
    # Query the consent preferences collection

    # Generate a unique cache key using dp_id and df_id
    cache_key = f"consent_preferences:{dp_id}:{df_id}"

    # Try to retrieve the data from Redis cache
    cached_data = r.get(cache_key)
    if cached_data:
        # If cache hit, return the data from Redis
        return json.loads(cached_data)


    documents = list(
        consent_preferences_collection.find({"dp_id": dp_id, "df_id": df_id, "is_active_consent_preference": True})
    )

    if not documents:
        raise HTTPException(
            status_code=404, detail="No preferences found for the given IDs"
        )

    # Collect all unique cp_ids from the documents
    cp_ids = {doc["cp_id"] for doc in documents}

    # Query the collection points collection for all relevant collection points
    collection_points = list(
        collection_point_collection.find(
            {"_id": {"$in": [ObjectId(cp_id) for cp_id in cp_ids]}}
        )
    )

    # Create a mapping from cp_id and data_element to its title and purposes
    cp_data_element_mapping = {}
    for collection_point in collection_points:
        cp_id_str = str(collection_point["_id"])
        for element in collection_point.get("data_elements", []):
            purposes = {
                purpose["purpose_id"]: purpose["purpose_description"]
                for purpose in element.get("purposes", [])
            }
            cp_data_element_mapping[(cp_id_str, element["data_element"])] = {
                "title": element.get("data_element_title", "Unknown data element"),
                "purposes": purposes,
            }

    # Transform documents into the desired format and group by 'name'
    grouped_result = defaultdict(list)
    for doc in documents:
        consent_document = doc.get("consent_document", {})
        consent_scope = consent_document.get("consent", {}).get("consent_scope", [])

        for scope in consent_scope:
            cp_id = doc["cp_id"]
            data_element_key = scope.get("data_element")

            # Try to fetch data using both cp_id and data_element
            data_element_info = cp_data_element_mapping.get(
                (cp_id, data_element_key),
                {"title": "Unknown data element", "purposes": {}},
            )

            data_element_title = data_element_info.get("title", "Unknown data element")
            purpose_descriptions = data_element_info.get("purposes", {})

            for consent in scope.get("consents", []):
                purpose_id = consent.get("purpose_id")
                purpose_description = purpose_descriptions.get(
                    purpose_id, f"Unknown purpose (ID: {purpose_id})"
                )

                consent_data = {
                    "cp_id": cp_id,  # Include cp_id in the response
                    "cp_name": consent_document.get("consent", {}).get("cp_name", ""),
                    "de_name": data_element_title,
                    "description": {
                        "activity": purpose_description,
                        "consent": consent.get("consent_timestamp", ""),
                        "validTill": consent.get("purpose_expiry", ""),
                        "agreement": consent_document.get("consent", {}).get(
                            "agreement_id", ""
                        ),
                        "retentionTill": consent.get("purpose_retention", ""),
                        "consent_status": consent.get("consent_status", ""),
                        "consent_id": purpose_id,
                        "revokedDate": consent.get("revoked_date", ""),
                        "purpose_mandatory": consent.get("purpose_mandatory", {}),
                        "purpose_legal": consent.get("purpose_legal", {}),
                        "purpose_revokable": consent.get("purpose_revokable", False),
                        "purpose_shared": consent.get("purpose_shared", False),
                    },
                }
                grouped_result[data_element_title].append(consent_data)

    # Convert the grouped result to the final format
    result = {name: consents for name, consents in grouped_result.items()}

    r.set(cache_key, json.dumps(result), ex=3600)  # Cache for 1 hour (3600 seconds)

    return result


@consentRouter.post("/revoke-consent", tags=["Consent Preference"])
async def revoke_consent(
    request: Request,
    dp_id: str = Query(..., description="Data Principal ID"),
    df_id: str = Query(..., description="Data Fiduciary ID"),
    consent_id: str = Query(..., description="Consent ID to Revoke"),
    consent_status: bool = Query(..., description="Consent Status"),
):
    try:
        # Find the document that matches the dp_id and df_id
        document = consent_preferences_collection.find_one(
            {"dp_id": dp_id, "df_id": df_id, "is_active_consent_preference": True}
        )

        if not document:
            raise HTTPException(
                status_code=404, detail="No consent preferences found for the given IDs"
            )

        consent_scope = (
            document.get("consent_document", {})
            .get("consent", {})
            .get("consent_scope", [])
        )
        consent_updated = False

        # Iterate through consent scopes and update the consent status
        for scope in consent_scope:
            for consent in scope.get("consents", []):
                if consent.get("purpose_id") == consent_id:

                    if consent["consent_status"] == consent_status:
                        raise HTTPException(
                            status_code=400,
                            detail="Consent status is already set to the given value",
                        )

                    if not consent_status:
                        consent["consent_status"] = False
                        consent["revoked_date"] = datetime.utcnow().isoformat()  # Set revoked_date

                        # Update the document in the collection
                        update_result = consent_preferences_collection.update_one(
                            {"_id": document["_id"]},
                            {"$set": {"consent_document.consent.consent_scope": consent_scope}},
                        )

                        if update_result.modified_count == 0:
                            raise HTTPException(
                                status_code=500, detail="Failed to update consent preferences"
                            )

                    else:
                        consent_preferences_collection.update_one(
                            {"_id": document["_id"]},
                            {"$set": {"is_active_consent_preference": False}},
                        )

                        consent["consent_status"] = True

                        linked_agreement_id = document.get("consent_document", {}).get("consent", {}).get("agreement_id", "")

                        # Update the consent's expiry date
                        current_expiry_date = datetime.fromisoformat(consent["purpose_expiry"])

                        # Calculate new expiry date
                        collection_point = collection_point_collection.find_one(
                            {
                                "_id": ObjectId(document.get("cp_id", "")),
                                "application_id": document.get("app_id", ""),
                            }
                        )
                        if not collection_point:
                            raise HTTPException(
                                status_code=404, detail="Collection point not found"
                            )

                        data_elements = collection_point.get("data_elements", [])
                        matching_element = next(
                            (
                                e
                                for e in data_elements
                                if e["data_element"] == scope.get("data_element")
                            ),
                            None,
                        )
                        if matching_element:
                            expiry_days = matching_element.get("expiry", 0)
                            new_expiry_date = calculate_future_date(current_expiry_date, expiry_days)

                            consent["purpose_expiry"] = new_expiry_date

                        document["consent_document"]["consent"]["linked_agreement"] = linked_agreement_id

                        # Generate hash for consent_document
                        consent_hash = generate_body_hash(document["consent_document"])
                        document["consent_document"]["consent"]["agreement_hash_id"] = consent_hash

                        document["_id"] = str(document["_id"])
                        if "cp_id" in document:
                            document["cp_id"] = str(document["cp_id"])

                        # Save request headers and body in user_consent_headers collection
                        body_hash = generate_body_hash(document)
                        user_consent_document = {
                            "headers": dict(request.headers),
                            "body": document,
                            "body_hash": body_hash,
                            "timestamp": datetime.utcnow().isoformat(),
                        }

                        # Insert document and get inserted ID
                        user_consent_result = user_consent_headers.insert_one(user_consent_document)
                        user_consent_id = user_consent_result.inserted_id

                        # Interact with blockchain or similar service to get agreement_id
                        agreement_id = harsh_blockchain_functionationing(document["consent_document"])
                        document["consent_document"]["consent"]["agreement_id"] = agreement_id

                        document["user_consent_request_id"] = str(user_consent_id)

                        document["is_active_consent_preference"] = True

                        document["_id"] = ObjectId()  # Create a new document ID for the new version

                        consent_preferences_collection.insert_one(document)

                    consent_updated = True

        if not consent_updated:
            raise HTTPException(
                status_code=404, detail="Consent ID not found in the given preferences"
            )
        
        #updating the redis cache after revoking the consent
        cache_key = f"consent_preferences:{dp_id}:{df_id}"
        r.delete(cache_key)

        return {"detail": "Consent successfully revoked"}
    except WriteError as e:
        raise HTTPException(status_code=500, detail=f"Database write error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
