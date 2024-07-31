from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from app.models.models import DeveloperDetails, ApplicationDetails
from app.config.db import (
    developer_details_collection,
    organisation_collection,
    application_collection,
)
from bson import ObjectId
from datetime import datetime
import secrets
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from limits.storage import RedisStorage

# Initialize the RedisStorage for SlowAPI
redis_url = "redis://localhost:6379/0"
storage = RedisStorage(redis_url)
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)

registerUser = APIRouter()

@registerUser.post("/package-register", tags=["Package register & application"])
@limiter.limit("2/minute")
async def package_register(request: Request, data: DeveloperDetails):
    headers = dict(request.headers)
    client_ip = request.client.host

    org_key = secrets.token_urlsafe(16)
    org_secret = secrets.token_urlsafe(32)

    developer_data = data.dict()
    developer_data["headers"] = headers
    developer_data["client_ip"] = client_ip
    developer_data["org_key"] = org_key
    developer_data["org_secret"] = org_secret
    developer_data["registered_at"] = datetime.utcnow()

    dev_result = developer_details_collection.insert_one(developer_data)
    if not dev_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert developer details"
        )

    inserted_dev_id = str(dev_result.inserted_id)

    organisation_data = {
        "organisation_name": data.organisation_name,
        "developer_email": data.developer_email,
        "developer_details_id": inserted_dev_id,
        "registered_at": datetime.utcnow(),
    }
    org_result = organisation_collection.insert_one(organisation_data)
    inserted_org_id = str(org_result.inserted_id)

    developer_details_collection.update_one(
        {"_id": ObjectId(inserted_dev_id)},
        {"$set": {"organisation_id": inserted_org_id}},
    )

    return JSONResponse(
        content={
            "con_org_id": inserted_org_id,
            "con_org_key": org_key,
            "con_org_secret": org_secret,
        }
    )


@registerUser.post("/create-application", tags=["Package register & application"])
@limiter.limit("6/minute")
async def create_application(
    request:Request,
    data: ApplicationDetails,
    org_key: str = Header(...),
    org_secret: str = Header(...),
    org_id: str = Header(...),
):
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    app_id = secrets.token_hex(8)

    valid_types = ["web app", "mobile app", "ctv", "pos", "other"]
    if data.app_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid app_type. Must be one of: {', '.join(valid_types)}",
        )

    valid_stages = ["development", "production", "testing"]
    if data.app_stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid app_stage. Must be one of: {', '.join(valid_stages)}",
        )

    valid_users = ["global", "india", "eu", "usa", "saudi arabia"]
    if data.application_user not in valid_users:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid application_user. Must be one of: {', '.join(valid_users)}",
        )

    app_data = data.dict()
    app_data["org_id"] = org_id
    app_data["app_id"] = app_id
    app_data["registered_at"] = datetime.utcnow()

    app_result = application_collection.insert_one(app_data)
    if not app_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert application details"
        )

    yaml_data = {
        "version": "1.0",
        "organisation_id": org_id,
        "applications": [
            {
                "application_id": app_id,
                "type": data.app_type,
                "name": data.app_name,
                "stage": data.app_stage,
                "application_user": data.application_user,
                "collection_points_data": [],
            }
        ],
    }

    return JSONResponse(
        content={
            "yaml_data": yaml_data,
            "con_app_id": app_id,
            "app_type": data.app_type,
            "app_name": data.app_name,
            "app_stage": data.app_stage,
            "application_user": data.application_user,
        }
    )
