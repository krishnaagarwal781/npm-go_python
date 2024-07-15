from pydantic import BaseModel
from pymongo import MongoClient
from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import secrets
import datetime
import yaml
from bson import ObjectId


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
    app_id: str
    org_key: str
    org_secret: str


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

    # Generate org_key and org_secret
    org_key = secrets.token_urlsafe(16)
    org_secret = secrets.token_urlsafe(32)

    # Prepare the data to insert into MongoDB
    developer_data = data.dict()
    developer_data["headers"] = headers
    developer_data["client_ip"] = client_ip
    developer_data["org_key"] = org_key
    developer_data["org_secret"] = org_secret
    developer_data["registered_at"] = datetime.datetime.utcnow()

    # Insert data into developer_details collection
    dev_result = developer_details_collection.insert_one(developer_data)
    if not dev_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert developer details"
        )

    # Get the generated ObjectId and convert it to string
    inserted_dev_id = str(dev_result.inserted_id)

    # Update developer_details collection with string format organisation_id

    # Insert data into organisation collection using the inserted ObjectId
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

    if not org_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert organisation details"
        )

    # Save secrets in .env file and consent.md file
    with open(".env", "w") as f:
        f.write(
            f"ORG_ID={inserted_org_id}\nORG_KEY={org_key}\nORG_SECRET={org_secret}\n"
        )
    with open("consent.md", "w") as f:
        f.write("## Consent Manager Documentation\n")
        f.write(f"### Organisation ID: {inserted_dev_id}\n")
        f.write(f"### Organisation Key: {org_key}\n")
        f.write(f"### Organisation Secret: {org_secret}\n")

    return JSONResponse(
        content={
            "org_id": inserted_dev_id,
            "org_key": org_key,
            "org_secret": org_secret,
        }
    )


@app.post("/create-application")
async def create_application(
    data: ApplicationDetails,
    org_id: str,
    org_key: str,
    org_secret: str,
):
    # Verify org_key and org_secret
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    # Generate app_id
    app_id = secrets.token_hex(8)

    # Prepare the data to insert into MongoDB
    app_data = data.dict()
    app_data["org_id"] = org_id
    app_data["app_id"] = app_id
    app_data["registered_at"] = datetime.datetime.utcnow()

    # Insert data into application_collection
    app_result = application_collection.insert_one(app_data)
    if not app_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert application details"
        )

    # Update YAML template
    yaml_template = {
        "version": "1.0",
        "applications": [
            {"application_id": app_id, "type": data.app_type, "collection_points": []}
        ],
    }

    with open(f"{org_id}_applications.yaml", "w") as yaml_file:
        yaml.dump(yaml_template, yaml_file)

    return JSONResponse(content={"app_id": app_id, "app_type": data.app_type})


@app.post("/create-collection-point")
async def create_collection_point(data: CollectionPointRequest):
    # Verify org_key and org_secret
    organisation = developer_details_collection.find_one(
        {
            "organisation_id": data.org_id,
            "org_key": data.org_key,
            "org_secret": data.org_secret,
        }
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    # Prepare the data to insert into MongoDB
    collection_point_data = data.dict()
    collection_point_data["registered_at"] = datetime.datetime.utcnow()

    # Insert data into collection_point_collection
    cp_result = collection_point_collection.insert_one(collection_point_data)
    if not cp_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert collection point details"
        )

    # Get the inserted _id from MongoDB and convert it to string for cp_id
    cp_id = str(cp_result.inserted_id)

    # Update YAML template with cp_id
    with open(f"{data.org_id}_applications.yaml", "r") as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)
    # collection_point_data["_id"] = str(collection_point_data["_id"])
    del collection_point_data["_id"]
    collection_point_data["registered_at"] = str(collection_point_data["registered_at"])
    
    for application in yaml_data["applications"]:
        if application["application_id"] == data.app_id:
            application["collection_points"].append(
                {"collection_point_id": cp_id, "cp_details": collection_point_data}
            )

    with open(f"{data.org_id}_applications.yaml", "w") as yaml_file:
        yaml.dump(yaml_data, yaml_file)

    return JSONResponse(content={"cp_id": cp_id})


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

    # Read and parse YAML data from the uploaded file
    yaml_content = await yaml_file.read()
    yaml_data = yaml.safe_load(yaml_content)

    # Extract applications and collection points
    applications = yaml_data.get("applications", [])
    operation_update = []

    for application in applications:
        if application["application_id"] == app_id:
            collection_points = application["collection_points"]

            for cp in collection_points:
                cp_id = cp["collection_point_id"]

                # Check if the collection point already exists
                existing_cp = collection_point_collection.find_one(
                    {"org_id": org_id, "app_id": app_id, "cp_id": cp_id}
                )

                if existing_cp:
                    # Update existing collection point
                    del cp["cp_details"]["_id"]
                    result = collection_point_collection.update_one(
                        {"_id": existing_cp["_id"]}, {"$set": cp["cp_details"]}
                    )
                    if result.modified_count > 0:
                        operation_update.append(
                            {"cp_id": cp_id, "operation": "updated"}
                        )
                else:
                    # Insert new collection point
                    cp_data = cp["cp_details"]
                    cp_data["org_id"] = org_id
                    cp_data["app_id"] = app_id
                    cp_data["cp_id"] = cp_id
                    cp_data["registered_at"] = datetime.datetime.utcnow()

                    result = collection_point_collection.insert_one(cp_data)
                    if result.acknowledged:
                        operation_update.append(
                            {"cp_id": cp_id, "operation": "created"}
                        )

    # Update YAML template
    with open(f"{org_id}_applications.yaml", "w") as yaml_file:
        yaml.dump(yaml_data, yaml_file)

    return JSONResponse(content={"operation_update": operation_update})


@app.delete("/delete-collection-point")
async def delete_collection_point(
    org_id: str,
    app_id: str,
    org_key: str,
    org_secret: str,
    cp_id: str,
):
    try:
        # Verify org_key and org_secret
        organisation = developer_details_collection.find_one(
            {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
        )
        if not organisation:
            raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

        # Delete the collection point from the database
        delete_result = collection_point_collection.delete_one(
            {"org_id": org_id, "app_id": app_id, "_id": ObjectId(cp_id)}
        )
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Collection point not found")

        # Update YAML template
        with open(f"{org_id}_applications.yaml", "r") as yaml_file:
            yaml_data = yaml.safe_load(yaml_file)

        for application in yaml_data["applications"]:
            if application["application_id"] == app_id:
                application["collection_points"] = [
                    cp
                    for cp in application["collection_points"]
                    if cp["collection_point_id"] != cp_id
                ]

        with open(f"{org_id}_applications.yaml", "w") as yaml_file:
            yaml.dump(yaml_data, yaml_file)

        return JSONResponse(
            content={"message": "Collection point deleted successfully"}
        )

    except Exception as e:
        return JSONResponse(
            content={"message": f"Failed to process request. Error: {str(e)}"},
            status_code=500,
        )


@app.get("/get-collection-point")
async def get_collection_point(
    org_id: str,
    app_id: str,
    org_key: str,
    org_secret: str,
):
    try:
        # Verify org_key and org_secret
        organisation = developer_details_collection.find_one(
            {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
        )
        if not organisation:
            raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

        # Fetch collection points for the given org_id and app_id
        collection_points = collection_point_collection.find(
            {"org_id": org_id, "app_id": app_id}
        )

        # Convert collection points to a list of dictionaries
        collection_points_list = []
        for cp in collection_points:
            # Convert ObjectId to string for serialization
            cp["_id"] = str(cp["_id"])
            cp["registered_at"] = str(cp["registered_at"])
            collection_points_list.append(cp)

        return JSONResponse(content={"collection_points": collection_points_list})

    except Exception as e:
        return JSONResponse(
            content={"message": f"Failed to process request. Error: {str(e)}"},
            status_code=500,
        )
