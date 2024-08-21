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

consentRouter = APIRouter()

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
    # Validate collection point and fetch data elements
    collection_point = collection_point_collection.find_one(
        {"_id": ObjectId(cp_id), "application_id": application_id}
    )
    if not collection_point:
        raise HTTPException(status_code=404, detail="Collection point not found")

    # Print collection point to debug
    print(collection_point)

    # Extract data elements
    data_elements = collection_point.get("data_elements", [])

    # Validate data elements
    data_elements_ids = {element["data_element"] for element in data_elements}
    for element in data.data_elements:
        if element.data_element not in data_elements_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data_element: {element.data_element}",
            )

    # Calculate dates for each data element
    consent_scope = []
    for element in data.data_elements:
        # Find matching element in collection_point
        matching_element = next(
            (e for e in data_elements if e["data_element"] == element.data_element),
            None,
        )
        if matching_element:
            expiry_days = matching_element.get("expiry", 0)
            retention_days = matching_element.get("retention_period", 0)

            # Calculate dates
            expiry_date = calculate_future_date(datetime.utcnow(), expiry_days)
            retention_date = calculate_future_date(datetime.utcnow(), retention_days)

            consent_scope.append(
                {
                    "data_element": element.data_element,
                    "consents": [
                        {
                            "purpose_id": consent.purpose_id,
                            "consent_status": consent.consent_status,
                            "shared": consent.shared,
                            "data_processors": consent.data_processors,
                            "cross_border": False,
                            "encryption": None,
                            "sensitive": None,
                            "consent_timestamp": consent.consent_timestamp,
                            "expiry_date": expiry_date,
                            "retention_date": retention_date,
                        }
                        for consent in element.consents
                    ],
                }
            )

    # Build consent document
    consent_document = {
        "consent": {
            "context": "https://consent.foundation/artifact/v1",
            "cp_name": collection_point.get("cp_name", ""),
            "agreement_hash_id": "",  # To be updated
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
            "consent_scope": consent_scope,
            "timestamp": datetime.utcnow().isoformat(),
            "agreement_id": "",  # To be updated
        },
    }

    # Generate hash for consent_document
    consent_hash = generate_body_hash(consent_document)
    consent_document["consent"]["agreement_hash_id"] = consent_hash

    # Save request headers and body in user_consent_headers collection
    body_hash = generate_body_hash(data.dict())
    user_consent_document = {
        "headers": dict(request.headers),
        "body": data.dict(),
        "body_hash": body_hash,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Insert document and get inserted ID
        user_consent_result = user_consent_headers.insert_one(user_consent_document)
        user_consent_id = user_consent_result.inserted_id

        # Interact with blockchain or similar service to get agreement_id
        agreement_id = harsh_blockchain_functionationing(consent_document)
        consent_document["consent"]["agreement_id"] = agreement_id

        # Insert or update consent document in MongoDB
        consent_preferences_collection.update_one(
            {"df_id": df_id, "app_id": application_id, "cp_id": cp_id, "dp_id": dp_id},
            {
                "$set": {
                    "consent_document": consent_document,
                    "user_consent_request_id": str(user_consent_id),
                }
            },
            upsert=True,
        )

        return JSONResponse(
            content={
                "message": "Consent preferences updated successfully",
                "agreement_id": agreement_id,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@consentRouter.get("/get-preferences", tags=["Consent Preference"])
async def get_preferences(
    dp_id: str = Query(..., description="Data Principal ID"),
    df_id: str = Query(..., description="Data Fiduciary ID"),
):
    # Query the consent preferences collection
    documents = list(
        consent_preferences_collection.find({"dp_id": dp_id, "df_id": df_id})
    )

    if not documents:
        raise HTTPException(
            status_code=404, detail="No preferences found for the given IDs"
        )

    # Collect all unique purpose_ids and data_elements
    purpose_ids = set()
    data_elements_set = set()
    for doc in documents:
        consent_scope = (
            doc.get("consent_document", {}).get("consent", {}).get("consent_scope", [])
        )
        for scope in consent_scope:
            data_elements_set.add(scope.get("data_element"))
            for consent in scope.get("consents", []):
                purpose_ids.add(consent.get("purpose_id"))

    # Fetch purpose descriptions and data element titles
    purpose_descriptions = {}
    data_element_titles = {}
    if purpose_ids or data_elements_set:
        # Fetch the collection points document based on cp_id from the first document
        cp_id = documents[0].get("cp_id")
        if cp_id:
            collection_point = collection_point_collection.find_one(
                {"_id": ObjectId(cp_id)}
            )
            if collection_point:
                data_elements = collection_point.get("data_elements", [])
                for element in data_elements:
                    data_element_id = element.get("data_element")
                    data_element_title = element.get("data_element_title")
                    purposes = element.get("purposes", [])
                    if data_element_id in data_elements_set:
                        data_element_titles[data_element_id] = data_element_title
                    for purpose in purposes:
                        if purpose["purpose_id"] in purpose_ids:
                            purpose_descriptions[purpose["purpose_id"]] = purpose[
                                "purpose_description"
                            ]

    # Transform documents into the desired format
    result = []
    for doc in documents:
        consent_document = doc.get("consent_document", {})
        consent_scope = consent_document.get("consent", {}).get("consent_scope", [])

        for scope in consent_scope:
            data_element_id = scope.get("data_element", "")
            data_element_title = data_element_titles.get(data_element_id, "Unknown data element")

            for consent in scope.get("consents", []):
                purpose_description = purpose_descriptions.get(
                    consent.get("purpose_id"), "Unknown purpose"
                )

                consent_data = {
                    "name": data_element_title,  # Set name to data_element_title
                    "description": {
                        "activity": purpose_description,
                        "consent": consent.get("consent_timestamp", ""),
                        "validTill": consent.get("expiry_date", ""),
                        "agreement": consent_document.get("consent", {}).get(
                            "agreement_id", ""
                        ),
                        "retentionTill": consent.get("retention_date", ""),
                    },
                }
                result.append(consent_data)

    return result