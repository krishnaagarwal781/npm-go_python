from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Request
from fastapi.responses import JSONResponse
from bson import ObjectId
import datetime
import secrets
import yaml
from app.config.db import collection_point_collection, developer_details_collection, translated_data_element_collection, consent_directory_languages_collection
from app.models.models import CollectionPointRequest
from app.schemas.utils import save_data_to_concur
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from limits.storage import RedisStorage
import requests

collectionRouter = APIRouter()
redis_url = "redis://default:GtOhsmeCwPJsZC8B0A8R2ihcA7pDVXem@redis-11722.c44.us-east-1-2.ec2.cloud.redislabs.com:11722/0"  # Adjust the Redis URL as needed
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)


@collectionRouter.post("/create-collection-point", tags=["Collection Point Management"])
@limiter.limit("5/minute")
async def create_collection_point(
    request: Request,
    data: CollectionPointRequest,
    org_id: str = Header(...),
    org_key: str = Header(...),
    org_secret: str = Header(...),
    application_id: str = Header(...),
):
    organisation = developer_details_collection.find_one(
        {
            "organisation_id": org_id,
            "org_key": org_key,
            "org_secret": org_secret,
        }
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")
    
        # Assign purpose_id to each purpose before processing
    for de in data.data_elements:
        for purpose in de.purposes:
            purpose.purpose_id = secrets.token_hex(8)  # Generate a unique purpose_id

    collection_point_data = {
        "org_id": org_id,
        "application_id": application_id,
        "cp_name": data.cp_name,
        "cp_status": "active",
        "data_elements": [
            {
                "data_element": de.data_element,
                "data_element_collection_status": "active",
                "data_element_title": de.data_element_title,
                "data_element_description": de.data_element_description,
                "data_owner": de.data_owner,
                "legal_basis": de.legal_basis,
                "retention_period": de.retention_period,
                "cross_border": False,
                "sensitive": False,
                "encrypted": False,
                "expiry": de.expiry,
                "purposes": [
                    {
                        "purpose_id": purpose.purpose_id,
                        "purpose_description": purpose.purpose_description,
                        "purpose_language": purpose.purpose_language,
                    }
                    for purpose in de.purposes
                ],
            }
            for de in data.data_elements
        ],
        "registered_at": datetime.datetime.utcnow(),
    }

    try:
        cp_result = collection_point_collection.insert_one(collection_point_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to insert collection point details: {str(e)}",
        )

    cp_id = str(cp_result.inserted_id)
    cp_url = f"demo.api.com/{cp_id}"

    try:
        collection_point_collection.update_one(
            {"_id": cp_result.inserted_id}, {"$set": {"cp_url": cp_url}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update collection point URL: {str(e)}"
        )

    for de in data.data_elements:
        #saving data for translation
        all_languages = list(consent_directory_languages_collection.find())
        translated_element_structure = []
        for lang in all_languages:
            translated_element_structure.append({
                "lang_title": lang["lang_title"],
                "lang_display": lang["lang_display"],
                "lang_short_code": lang["lang_short_code"],
                "translation_symbol": lang["translation_symbol"],
                "data_element_concur_name": de.data_element_title if lang["lang_short_code"] == "en" else "",
            })
        translated_data_element_payload = {
            "cp_id": cp_id,
            "translated_elements": translated_element_structure,
            "is_translated": False,
        }

        try:
            translated_data_element_id = translated_data_element_collection.insert_one(translated_data_element_payload).inserted_id
            collection_point_collection.update_one(
                {"_id": cp_result.inserted_id, "data_elements.data_element": de.data_element},
                {"$set": {"data_elements.$.translated_data_element_id": str(translated_data_element_id)}},
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to insert translated data element details: {str(e)}",
            )


    for de in data.data_elements:
        payload = {
            "data_element_type": de.data_element,
            "data_element_concur_name": de.data_element_title,
            "data_element_short_description": de.data_element_description,
            "data_element_original_name": de.data_element,
            "added_by": "",
            "can_be_identifier": False,
            "has_personal_info": False,
            "is_sensitive_data": False,
            "consent_required": True,
            "third_party_vendor": False,
            "cross_border": False,
            "is_field_encrypted": False,
            "collection_points": [cp_id],
            "publish_date": datetime.datetime.utcnow().isoformat(),
            "data_element_mapping": "string",
            "status": "active",
            "related_data_element": [],
            "data_element_classification_tag": "string",
        }

        concur_response = save_data_to_concur(org_id, payload)
        if not concur_response:
            raise HTTPException(
                status_code=500, detail="Failed to save data to Concur service"
            )

    # Adding Purposes to consent directory
    purposes_payload = {
        "industry": ["66a4cf825cb74730faf48626"],
        "sub_category": "Customer Support",  # Replace with the appropriate value
        "purpose": [
            {
                "description": purpose.purpose_description,
                "lang_short_code": purpose.purpose_language,
            }
            for de in data.data_elements
            for purpose in de.purposes
        ],
    }

    # Create a mapping of purpose_id to the index in purposes list
    purpose_idx_map = {}
    for de_idx, de in enumerate(data.data_elements):
        for idx, purpose in enumerate(de.purposes):
            purpose_idx_map[purpose.purpose_id] = (de_idx, idx)

    try:
        api_url = "https://consent-foundation.adnan-qasim.me/add-purpose"
        api_headers = {"Content-Type": "application/json"}
        api_response = requests.post(api_url, json=purposes_payload, headers=api_headers)
        api_response.raise_for_status()

        # Extract the inserted_ids from the response
        api_response_data = api_response.json()
        inserted_ids = api_response_data.get("inserted_ids", [])

        if not inserted_ids or len(inserted_ids) != len(purpose_idx_map):
            raise HTTPException(
                status_code=500,
                detail="Mismatch in number of translated_purpose_ids returned from the consent directory"
            )

        # Update the collection_point_collection with translated_purpose_id
        for purpose_id, inserted_id in zip(purpose_idx_map.keys(), inserted_ids):
            de_idx, purpose_idx = purpose_idx_map[purpose_id]
            collection_point_collection.update_one(
                {
                    "_id": cp_result.inserted_id,
                    f"data_elements.{de_idx}.purposes.{purpose_idx}.purpose_id": purpose_id,
                },
                {
                    "$set": {
                        f"data_elements.{de_idx}.purposes.{purpose_idx}.translated_purpose_id": inserted_id,
                    }
                }
            )

    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send purposes to the consent directory: {str(e)}",
        )

    response_data = {
        "cp_id": cp_id,
        "cp_name": data.cp_name,
        "cp_status": "active",
        "cp_url": cp_url,
        "data_elements": [
            {
                "data_element": de.data_element,
                "data_element_collection_status": "active",
                "data_element_title": de.data_element_title,
                "data_element_description": de.data_element_description,
                "data_owner": de.data_owner,
                "legal_basis": de.legal_basis,
                "retention_period": de.retention_period,
                "cross_border": False,
                "sensitive": False,
                "encrypted": False,
                "expiry": de.expiry,
                "purposes": [
                    {
                        "purpose_id": purpose.purpose_id,
                        "purpose_description": purpose.purpose_description,
                        "purpose_language": purpose.purpose_language,
                    }
                    for purpose in de.purposes
                ],
            }
            for de in data.data_elements
        ],
    }

    return JSONResponse(
        content={
            "message": f"Collection point with id {cp_id} created successfully",
            "collection_point_data": response_data,
        }
    )


@collectionRouter.post("/push-yaml", tags=["Collection Point Management"])
@limiter.limit("5/minute")
async def push_yaml(
    request: Request,
    yaml_file: UploadFile = File(...),
    org_id: str = Header(...),
    app_id: str = Header(...),
    org_key: str = Header(...),
    org_secret: str = Header(...),
):
    # Validate the organization credentials
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    try:
        yaml_data = yaml.safe_load(yaml_file.file)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML file: {exc}")

    if not yaml_data.get("applications"):
        raise HTTPException(
            status_code=400, detail="No applications found in YAML file"
        )

    updated_count = 0

    for application in yaml_data.get("applications", []):
        if application.get("application_id") == app_id:
            for cp_details in application.get("collection_points_data", []):
                cp_id = cp_details.get("cp_id")
                if cp_id:
                    existing_cp = collection_point_collection.find_one(
                        {"_id": ObjectId(cp_id)}
                    )
                    if existing_cp:
                        # Process purposes to assign new purpose_id if needed
                        new_data_elements = []
                        for de in cp_details.get("data_elements", []):
                            new_purposes = []
                            for purpose in de.get("purposes", []):
                                if not purpose.get("purpose_id"):
                                    purpose["purpose_id"] = secrets.token_hex(8)
                                new_purposes.append(purpose)
                            new_de = de.copy()
                            new_de["purposes"] = new_purposes
                            new_data_elements.append(new_de)

                        update_result = collection_point_collection.update_one(
                            {"_id": ObjectId(cp_id)},
                            {
                                "$set": {
                                    "cp_name": cp_details.get(
                                        "cp_name", existing_cp.get("cp_name")
                                    ),
                                    "cp_status": cp_details.get(
                                        "cp_status", existing_cp.get("cp_status")
                                    ),
                                    "cp_url": cp_details.get(
                                        "cp_url", existing_cp.get("cp_url")
                                    ),
                                    "data_elements": new_data_elements,
                                }
                            },
                        )
                        if update_result.modified_count > 0:
                            updated_count += 1
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Collection point {cp_id} not found",
                        )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="collection_point_id is required for each collection point",
                    )

    if updated_count == 0:
        raise HTTPException(
            status_code=500,
            detail="No collection points were updated",
        )

    # Fetch the updated data from MongoDB
    updated_collection_points = list(
        collection_point_collection.find({"org_id": org_id, "application_id": app_id})
    )

    # Convert updated data to YAML format
    updated_yaml_data = {
        "version": "1.0",
        "organisation_id": org_id,
        "applications": [
            {
                "application_id": app_id,
                "type": application.get("type", ""),
                "name": application.get("name", ""),
                "stage": application.get("stage", ""),
                "application_user": application.get("application_user", ""),
                "collection_points_data": [
                    {
                        "cp_id": str(cp["_id"]),
                        "cp_name": cp.get("cp_name", ""),
                        "cp_status": cp.get("cp_status", ""),
                        "cp_url": cp.get("cp_url", ""),
                        "data_elements": cp.get("data_elements", []),
                    }
                    for cp in updated_collection_points
                ],
            }
            for application in yaml_data.get("applications", [])
            if application.get("application_id") == app_id
        ],
    }

    return JSONResponse(
        content={
            "message": f"YAML file updated successfully, {updated_count} collection points updated",
            "updated_yaml_data": updated_yaml_data,
        }
    )


@collectionRouter.delete(
    "/delete-collection-point", tags=["Collection Point Management"]
)
@limiter.limit("5/minute")
async def delete_collection_point(
    request: Request,
    collection_point_id: str = Header(...),
    org_id: str = Header(...),
    org_key: str = Header(...),
    org_secret: str = Header(...),
):
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    delete_result = collection_point_collection.delete_one(
        {"_id": ObjectId(collection_point_id), "org_id": org_id}
    )
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Collection point not found")

    return JSONResponse(content={"message": "Collection point deleted successfully"})


@collectionRouter.get("/get-collection-points", tags=["Collection Point Management"])
@limiter.limit("5/minute")
async def get_collection_points(
    request: Request,
    app_id: str = Header(...),
    org_id: str = Header(...),
    org_key: str = Header(...),
    org_secret: str = Header(...),
):
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    collection_points = list(
        collection_point_collection.find({"org_id": org_id, "application_id": app_id})
    )

    if not collection_points:
        raise HTTPException(status_code=404, detail="No collection points found")

    for cp in collection_points:
        cp["_id"] = str(cp["_id"])
        if "registered_at" in cp:
            cp["registered_at"] = cp["registered_at"].isoformat()
        if "data_elements" in cp:
            for data_element in cp["data_elements"]:
                for purpose in data_element.get("purposes", []):
                    if "purpose_date" in purpose:
                        purpose["purpose_date"] = purpose["purpose_date"].isoformat()

    return JSONResponse(content={"collection_points": collection_points})
