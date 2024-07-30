from fastapi import (
    FastAPI,
    HTTPException,
    Header,
    APIRouter,
)
from fastapi.responses import JSONResponse
from bson import ObjectId
from datetime import datetime
from app.config.db import (
    consent_preferences_collection,
    collection_point_collection,
    developer_details_collection,
)
from app.models.models import ConsentPreferenceRequest

consentRouter = APIRouter()


@consentRouter.post("/post-consent-preference",tags=["Consent Preference"])
async def post_consent_preference(data: ConsentPreferenceRequest):
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
    for scope_item in data.consent_scope:
        if not any(
            element["data_element"] == scope_item.data_element_name
            for element in data_elements
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data_element_name: {scope_item.data_element_name}",
            )

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
            "date_of_consent": datetime.datetime.utcnow().isoformat(),
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
        "consent_scope": [
            {
                "data_element_name": scope_item.data_element_name,
                "purpose_id": scope_item.purpose_id,
                "consent_status": scope_item.consent_status,
                "shared": scope_item.shared,
                "data_processor_id": scope_item.data_processor_id,
                "cross_border": scope_item.cross_border,
                "consent_timestamp": datetime.datetime.utcnow().isoformat(),
                "expiry_date": datetime.datetime.utcnow().isoformat(),
            }
            for scope_item in data.consent_scope
        ],
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
