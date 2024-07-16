from pydantic import BaseModel
from pymongo import MongoClient
from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import secrets
import datetime
from bson import ObjectId
from typing import List

class DeveloperDetails(BaseModel):
    developer_email: str
    developer_website: str
    developer_city: str
    developer_mobile: str
    organisation_name: str

class ApplicationDetails(BaseModel):
    app_type: str

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

    app_data = data.dict()
    app_data["org_id"] = org_id
    app_data["app_id"] = app_id
    app_data["registered_at"] = datetime.datetime.utcnow()

    app_result = application_collection.insert_one(app_data)
    if not app_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert application details"
        )

    return JSONResponse(
        content={
            "app_id": app_id,
            "app_type": data.app_type,
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

    collection_point_data = {
        "org_id": data.org_id,
        "app_id": data.application_id,
        "cp_name": "Default Collection Point",
        "cp_status": "active",
        "cp_url": "http://default-url.com",
        "data_elements": [
            {
                "data_element": "default_element",
                "data_element_title": "Default Element Title",
                "data_element_description": "Default Element Description",
                "data_owner": "Default Owner",
                "legal_basis": "Default Legal Basis",
                "retention_period": "1 year",
                "cross_border": False,
                "sensitive": False,
                "encrypted": True,
                "data_principal": True,
                "expiry": "Never",
                "data_element_collection_status": "active",
                "purposes": [
                    {
                        "purpose_id": "default_purpose_id",
                        "purpose_description": "Default Purpose Description",
                        "purpose_language": "EN",
                    }
                ],
            }
        ],
    }

    cp_result = collection_point_collection.insert_one(collection_point_data)
    if not cp_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert collection point details"
        )

    cp_id = str(cp_result.inserted_id)

    return JSONResponse(
        content={
            "message": f"Collection point with id {cp_id} created successfully",
            "collection_point_data": collection_point_data,
        }
    )

@app.post("/push-yaml")
async def push_yaml(
    yaml_data: dict,
    org_id: str = Form(...),
    app_id: str = Form(...),
    org_key: str = Form(...),
    org_secret: str = Form(...),
):
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    for application in yaml_data.get("applications", []):
        if application["application_id"] == app_id:
            for cp_details in application.get("collection_points", []):
                cp_id = cp_details.get("collection_point_id")
                existing_cp = collection_point_collection.find_one(
                    {"_id": ObjectId(cp_id)}
                )
                if existing_cp:
                    collection_point_collection.update_one(
                        {"_id": existing_cp["_id"]}, {"$set": cp_details["cp_details"]}
                    )
                else:
                    cp_data = {
                        "org_id": org_id,
                        "app_id": app_id,
                        "cp_name": cp_details["cp_details"]["cp_name"],
                        "cp_status": cp_details["cp_details"]["cp_status"],
                        "cp_url": cp_details["cp_details"]["cp_url"],
                        "data_elements": cp_details["cp_details"]["data_elements"],
                    }
                    cp_result = collection_point_collection.insert_one(cp_data)
                    cp_details["collection_point_id"] = str(cp_result.inserted_id)

    return JSONResponse(content={"message": "Collections points updated successfully"})

@app.delete("/delete-collection-point/{collection_point_id}")
async def delete_collection_point(
    collection_point_id: str, org_id: str, org_key: str, org_secret: str
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

@app.get("/get-collection-points/{app_id}")
async def get_collection_points(
    app_id: str, org_id: str, org_key: str, org_secret: str
):
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    collection_points = collection_point_collection.find(
        {"org_id": org_id, "app_id": app_id}
    )
    collection_points_data = []
    for cp in collection_points:
        collection_points_data.append(cp)

    return JSONResponse(content={"collection_points": collection_points_data})
