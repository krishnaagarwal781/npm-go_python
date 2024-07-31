from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Request
from fastapi.responses import JSONResponse
from bson import ObjectId
import datetime
import secrets
import yaml
from app.config.db import collection_point_collection, developer_details_collection
from app.models.models import CollectionPointRequest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from limits.storage import RedisStorage

collectionRouter = APIRouter()
redis_url = "redis://localhost:6379/0"  # Adjust the Redis URL as needed
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
                        "purpose_id": secrets.token_hex(8),
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

    for application in yaml_data.get("applications", []):
        if application.get("application_id") == app_id:
            for cp_details in application.get("collection_points_data", []):
                cp_id = cp_details.get("cp_id")
                if cp_id:
                    existing_cp = collection_point_collection.find_one(
                        {"_id": ObjectId(cp_id)}
                    )
                    if existing_cp:
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
                                    "data_elements": cp_details.get(
                                        "data_elements",
                                        existing_cp.get("data_elements"),
                                    ),
                                }
                            },
                        )
                        if update_result.modified_count == 0:
                            raise HTTPException(
                                status_code=500,
                                detail=f"Failed to update collection point {cp_id}",
                            )
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

    return JSONResponse(
        content={"message": "YAML file updated successfully", "yaml_data": yaml_data}
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
