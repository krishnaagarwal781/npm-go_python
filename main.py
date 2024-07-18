from pydantic import BaseModel
from pymongo import MongoClient
from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import secrets
import datetime
from bson import ObjectId
from typing import List
import yaml


class DeveloperDetails(BaseModel):
    developer_email: str
    developer_website: str
    developer_city: str
    developer_mobile: str
    organisation_name: str


class ApplicationDetails(BaseModel):
    app_type: str
    app_name: str
    app_stage: str
    application_user: str


class CollectionPointRequest(BaseModel):
    org_id: str
    org_key: str
    org_secret: str
    application_id: str


class Purpose(BaseModel):
    purpose_id: str
    purpose_description: str
    purpose_language: str


class DataElement(BaseModel):
    data_element: str
    data_element_title: str
    data_element_description: str
    data_owner: str
    legal_basis: str
    retention_period: str
    cross_border: bool
    sensitive: bool
    encrypted: bool
    data_principal: bool
    expiry: str
    data_element_collection_status: str
    purposes: List[Purpose]


class CollectionPointDetails(BaseModel):
    collection_point_id: str
    cp_name: str
    cp_status: str
    cp_url: str
    data_elements: List[DataElement]


class ApplicationDetailsExtended(BaseModel):
    application_id: str
    type: str
    collection_points: List[CollectionPointDetails]


class ApplicationDetailsRequest(BaseModel):
    org_id: str
    org_key: str
    org_secret: str
    application_details: ApplicationDetailsExtended


client = MongoClient(
    "mongodb+srv://sniplyuser:NXy7R7wRskSrk3F2@cataxprod.iwac6oj.mongodb.net/?retryWrites=true&w=majority"
)
db = client["python-go"]
developer_details_collection = db["developer_details"]
organisation_collection = db["organisation_details"]
application_collection = db["org_applications"]
collection_point_collection = db["collection_points"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/package-register")
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
    developer_data["registered_at"] = datetime.datetime.utcnow()

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
        "registered_at": datetime.datetime.utcnow(),
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


@app.post("/create-application")
async def create_application(
    data: ApplicationDetails,
    org_id: str,
    org_key: str,
    org_secret: str,
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
    app_data["registered_at"] = datetime.datetime.utcnow()

    app_result = application_collection.insert_one(app_data)
    if not app_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert application details"
        )

    # Prepare the YAML-like JSON structure to return
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


@app.post("/create-collection-point")
async def create_collection_point(data: CollectionPointRequest):
    organisation = developer_details_collection.find_one(
        {
            "organisation_id": data.org_id,
            "org_key": data.org_key,
            "org_secret": data.org_secret,
        }
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    # Prepare collection point data from the request
    collection_point_data = {
        "org_id": data.org_id,
        "application_id": data.application_id,
        "cp_name": "<Blank>",
        "cp_status": "active",
        "cp_url": "<URL>",
        "data_elements": [
            {
                "data_element": "<Blank>",
                "data_element_collection_status": "active",
                "data_element_title": "<Blank>",
                "data_element_description": "<Blank>",
                "data_owner": "<Blank>",
                "legal_basis": "<Blank>",
                "retention_period": "<Number> <days, month, year>",
                "cross_border": False,
                "sensitive": False,
                "encrypted": False,
                "expiry": "<Number> <days, month, year>",
                "purposes": [
                    {
                        "purpose_description": "<Blank>",
                        "purpose_language": "<EN, EU, HIN>",
                    }
                ],
            }
        ],
    }

    # Insert the collection point data into MongoDB
    cp_result = collection_point_collection.insert_one(collection_point_data)
    if not cp_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert collection point details"
        )

    # Retrieve the inserted cp_id
    cp_id = str(cp_result.inserted_id)

    # Remove the _id field before returning collection_point_data
    collection_point_data.pop("_id", None)
    collection_point_data.pop("application_id", None)
    collection_point_data.pop("org_id", None)

    # Include cp_id at the beginning of the collection point data response
    response_data = {
        "cp_id": cp_id,
        **collection_point_data,
    }

    return {
        "message": f"Collection point with id {cp_id} created successfully",
        "collection_point_data": response_data,
    }


@app.post("/push-yaml")
async def push_yaml(
    yaml_file: UploadFile = File(...),
    org_id: str = Form(...),
    app_id: str = Form(...),
    org_key: str = Form(...),
    org_secret: str = Form(...),
):
    # Verify org_key and org_secret
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    # Load YAML data
    try:
        yaml_data = yaml.safe_load(yaml_file.file)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML file: {exc}")

    # Process each collection point in YAML data
    for application in yaml_data.get("applications", []):
        if application.get("application_id") == app_id:
            for cp_details in application.get("collection_points_data", []):
                cp_id = cp_details.get("cp_id")
                if cp_id:
                    existing_cp = collection_point_collection.find_one(
                        {"_id": ObjectId(cp_id)}
                    )
                    if existing_cp:
                        # Update existing collection point
                        update_result = collection_point_collection.update_one(
                            {"_id": ObjectId(cp_id)},
                            {
                                "$set": {
                                    "cp_name": cp_details["cp_name"],
                                    "cp_status": cp_details["cp_status"],
                                    "cp_url": cp_details["cp_url"],
                                    "data_elements": cp_details["data_elements"],
                                    # Add more fields as needed
                                }
                            },
                        )
                        if update_result.modified_count == 0:
                            raise HTTPException(
                                status_code=500,
                                detail=f"Failed to update collection point {cp_id}",
                            )
                    else:
                        # Handle scenario where collection_point_id is not found
                        raise HTTPException(
                            status_code=404,
                            detail=f"Collection point {cp_id} not found",
                        )
                else:
                    # Handle scenario where collection_point_id is missing in YAML
                    raise HTTPException(
                        status_code=400,
                        detail="collection_point_id is required for each collection point",
                    )

    return JSONResponse(
        content={"message": "YAML file updated successfully", "yaml_data": yaml_data}
    )


@app.delete("/delete-collection-point/{collection_point_id}")
async def delete_collection_point(
    collection_point_id: str, org_id: str, org_key: str, org_secret: str
):
    # Verify org_key and org_secret
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    # Attempt to delete the collection point
    delete_result = collection_point_collection.delete_one(
        {"_id": ObjectId(collection_point_id), "org_id": org_id}
    )
    # Check if the collection point was not found
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Collection point not found")

    return JSONResponse(content={"message": "Collection point deleted successfully"})


@app.get("/get-collection-points/{app_id}")
async def get_collection_points(
    app_id: str, org_id: str, org_key: str, org_secret: str
):
    # Verify org_key and org_secret
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    # Retrieve collection points for the given org_id and app_id
    collection_points = list(
        collection_point_collection.find({"org_id": org_id, "application_id": app_id})
    )

    if not collection_points:
        raise HTTPException(status_code=404, detail="No collection points found")

    # Convert MongoDB ObjectId and datetime to string for JSON serialization
    for cp in collection_points:
        cp["_id"] = str(cp["_id"])
        if "registered_at" in cp:
            cp["registered_at"] = cp["registered_at"].isoformat()
        if "data_elements" in cp:
            for data_element in cp["data_elements"]:
                for purpose in data_element.get("purposes", []):
                    if "purpose_date" in purpose:
                        purpose["purpose_date"] = purpose["purpose_date"].isoformat()

    return JSONResponse(content={"con_collection_points": collection_points})
