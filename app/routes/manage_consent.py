from fastapi import FastAPI, HTTPException, Header, APIRouter, Request
from fastapi.responses import JSONResponse
from bson import ObjectId
from datetime import datetime
from app.config.db import (
    consent_preferences_collection,
    collection_point_collection,
    developer_details_collection,
)
from app.models.models import ConsentPreferenceRequest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from limits.storage import RedisStorage

consentRouter = APIRouter()

# Initialize RedisStorage and Limiter
redis_url = "redis://default:GtOhsmeCwPJsZC8B0A8R2ihcA7pDVXem@redis-11722.c44.us-east-1-2.ec2.cloud.redislabs.com:11722/0"  # Adjust the Redis URL as needed
storage = RedisStorage(redis_url)
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)


@consentRouter.post("/post-consent-preference", tags=["Consent Preference"])
@limiter.limit("5/minute")
async def post_consent_preference(request: Request, data: ConsentPreferenceRequest):
    # Validate organisation
    organisation = developer_details_collection.find_one(
        {
            "organisation_id": data.org_id,
            "org_key": data.org_key,
            "org_secret": data.org_secret,
        }
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    # Validate collection point and fetch data elements
    collection_point = collection_point_collection.find_one(
        {"_id": ObjectId(data.cp_id), "org_id": data.org_id}
    )
    if not collection_point:
        raise HTTPException(status_code=404, detail="Collection point not found")

    cp_name = collection_point.get("cp_name", "")
    data_elements = collection_point.get("data_elements", [])

    # Validate that each data_element_name in consent_scope exists in data_elements
    data_element_names = {element["data_element"] for element in data_elements}
    for scope_item in data.consent_scope:
        if scope_item.data_element_name not in data_element_names:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data_element_name: {scope_item.data_element_name}",
            )

    # Aggregate consents by data_element_name
    consents_by_element = defaultdict(list)

    for item in data.consent_scope:
        consents_by_element[item.data_element_name].append(
            {
                "purpose_id": item.purpose_id,
                "consent_status": item.consent_status,
                "shared": item.shared,
                "data_processor_id": item.data_processor_id,
                "cross_border": item.cross_border,
                "consent_timestamp": datetime.utcnow().isoformat(),
                "expiry_date": datetime.utcnow().isoformat(),
            }
        )

    # Build consent_scope in the required format
    consent_scope_aggregated = [
        {"data_element_name": key, "consents": value}
        for key, value in consents_by_element.items()
    ]

    # Build consent document
    consent_document = {
        "context": "https://consent.foundation/artifact/v1",
        "type": cp_name,
        "agreement_hash_id": "",
        "agreement_version": "",
        "linked_agreement_hash": "",
        "data_principal": {
            "dp_df_id": "",
            "dp_public_key": "",
            "dp_residency": "",
            "dp_email": "NULL [Encrypted]",
            "dp_verification": "",
            "dp_child": "",
            "dp_attorney": {
                "dp_df_id": "",
                "dp_public_key": "",
                "dp_email": "NULL [Encrypted]",
            },
        },
        "data_fiduciary": {
            "df_id": "",
            "agreement_date": "",
            "date_of_consent": datetime.utcnow().isoformat(),
            "consent_status": "active",
            "revocation_date": None,
        },
        "data_principal_rights": {
            "right_to_access": True,
            "right_to_rectify": True,
            "right_to_erase": True,
            "right_to_restrict_processing": True,
            "right_to_data_portability": True,
        },
        "consent_scope": consent_scope_aggregated,
        "dp_id": data.dp_id,
        "cp_id": data.cp_id,
    }

    # Insert or update the consent preference in MongoDB
    result = consent_preferences_collection.find_one_and_update(
        {"dp_id": data.dp_id, "cp_id": data.cp_id},
        {"$set": consent_document},
        upsert=True,
        return_document=True,
    )

    if result:
        return JSONResponse(
            content={
                "message": "Consent preferences updated successfully",
                "agreement_id": str(result["_id"]),
            }
        )
    else:
        inserted_id = str(
            consent_preferences_collection.insert_one(consent_document).inserted_id
        )
        return JSONResponse(
            content={
                "message": "Consent preferences created successfully",
                "agreement_id": inserted_id,
            }
        )
