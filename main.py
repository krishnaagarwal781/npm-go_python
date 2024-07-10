from pydantic import BaseModel
from pymongo import MongoClient
from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse, PlainTextResponse
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


class OrganisationDetails(BaseModel):
    organisation_name: str
    developer_email: str


class CollectionPointRequest(BaseModel):
    secret: str
    token: str


client = MongoClient(
    "mongodb+srv://sniplyuser:NXy7R7wRskSrk3F2@cataxprod.iwac6oj.mongodb.net/?retryWrites=true&w=majority"
)
db = client["python-go"]
developer_details_collection = db["developer_details"]
organisation_collection = db["organisation_details"]
collection_point_collection = db["collection_points"]


app = FastAPI()


@app.post("/package-register")
async def package_register(request: Request, data: DeveloperDetails):
    headers = dict(request.headers)

    # Generate a secret and token
    secret = secrets.token_hex(16)
    token = secrets.token_urlsafe(32)

    # Prepare the data to insert into MongoDB
    developer_data = data.dict()
    developer_data["headers"] = headers
    developer_data["secret"] = secret
    developer_data["token"] = token
    developer_data["registered_at"] = datetime.datetime.utcnow()

    # Insert data into developer_details collection
    dev_result = developer_details_collection.insert_one(developer_data)
    if not dev_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert developer details"
        )

    # Insert data into organisation collection
    organisation_data = {
        "organisation_name": data.organisation_name,
        "developer_email": data.developer_email,
        "developer_details_id": str(dev_result.inserted_id),
        "registered_at": datetime.datetime.utcnow(),
    }
    org_result = organisation_collection.insert_one(organisation_data)
    if not org_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert organisation details"
        )

    return JSONResponse(content={"secret": secret, "token": token})


@app.post("/create-collection-point")
async def create_collection_point(data: CollectionPointRequest):
    # Verify the secret and token
    secret = data.secret
    token = data.token
    if not secret or not token:
        raise HTTPException(status_code=400, detail="Secret and token are required")

    developer = developer_details_collection.find_one(
        {"secret": secret, "token": token}
    )
    if not developer:
        raise HTTPException(status_code=401, detail="Invalid secret or token")

    yaml_template = {
        "version": "1.0",
        "company": {
            "name": "Your Company Name",
            "website": "https://www.yourcompanywebsite.com",
            "company_id": "12345",
        },
        "applications": [
            {
                "application": {
                    "application_id": "app1",
                    "type": "Mobile",
                    "collection_points": [
                        {
                            "collection_point": {
                                "collection_point_id": "cp1",
                                "cp_name": "Collection Point 1",
                                "cp_url": "https://www.collectionpoint1.com",
                                "cp_status": "active",
                                "data_elements": [
                                    {
                                        "data_element": "home_address",
                                        "data_element_title": "Home Address",
                                        "data_element_description": "One line description of home address field",
                                        "data_element_collection_status": "active",
                                        "expiry": "90 days",
                                        "cross_border": False,
                                        "data_principal": False,
                                        "sensitive": True,
                                        "encrypted": True,
                                        "retention_period": "5 years",
                                        "data_owner": "Customer Service Department",
                                        "legal_basis": "Consent",
                                        "purposes": [
                                            {
                                                "purpose_id": "p1",
                                                "purpose_description": "Purpose description for home address",
                                                "purpose_language": "EN",
                                            },
                                            {
                                                "purpose_id": "p2",
                                                "purpose_description": "Another purpose for home address",
                                                "purpose_language": "EN",
                                            },
                                        ],
                                    },
                                    {
                                        "data_element": "phone_number",
                                        "data_element_title": "Phone Number",
                                        "data_element_description": "One line description of phone number field",
                                        "data_element_collection_status": "active",
                                        "expiry": "60 days",
                                        "cross_border": True,
                                        "data_principal": True,
                                        "sensitive": False,
                                        "encrypted": True,
                                        "retention_period": "3 years",
                                        "data_owner": "Marketing Department",
                                        "legal_basis": "Legitimate Interest",
                                        "purposes": [
                                            {
                                                "purpose_id": "p3",
                                                "purpose_description": "Purpose description for phone number",
                                                "purpose_language": "EN",
                                            },
                                            {
                                                "purpose_id": "p4",
                                                "purpose_description": "Another purpose for phone number",
                                                "purpose_language": "EN",
                                            },
                                        ],
                                    },
                                ],
                            },
                        },
                        {
                            "collection_point": {
                                "collection_point_id": "cp2",
                                "cp_name": "Collection Point 2",
                                "cp_url": "https://www.collectionpoint2.com",
                                "cp_status": "active",
                                "data_elements": [
                                    {
                                        "data_element": "email_address",
                                        "data_element_title": "Email Address",
                                        "data_element_description": "One line description of email address field",
                                        "data_element_collection_status": "active",
                                        "expiry": "30 days",
                                        "cross_border": True,
                                        "data_principal": True,
                                        "sensitive": False,
                                        "encrypted": True,
                                        "retention_period": "2 years",
                                        "data_owner": "Sales Department",
                                        "legal_basis": "Contractual Necessity",
                                        "purposes": [
                                            {
                                                "purpose_id": "p5",
                                                "purpose_description": "Purpose description for email address",
                                                "purpose_language": "EN",
                                            },
                                            {
                                                "purpose_id": "p6",
                                                "purpose_description": "Another purpose for email address",
                                                "purpose_language": "EN",
                                            },
                                        ],
                                    },
                                    {
                                        "data_element": "date_of_birth",
                                        "data_element_title": "Date of Birth",
                                        "data_element_description": "One line description of date of birth field",
                                        "data_element_collection_status": "active",
                                        "expiry": "365 days",
                                        "cross_border": False,
                                        "data_principal": True,
                                        "sensitive": True,
                                        "encrypted": True,
                                        "retention_period": "10 years",
                                        "data_owner": "HR Department",
                                        "legal_basis": "Legal Obligation",
                                        "purposes": [
                                            {
                                                "purpose_id": "p7",
                                                "purpose_description": "Purpose description for date of birth",
                                                "purpose_language": "EN",
                                            },
                                            {
                                                "purpose_id": "p8",
                                                "purpose_description": "Another purpose for date of birth",
                                                "purpose_language": "EN",
                                            },
                                        ],
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        ],
    }

    yaml_response = yaml.dump(yaml_template, default_flow_style=False)

    return PlainTextResponse(yaml_response, media_type="text/yaml")


@app.post("/post-collection-point")
async def post_collection_point(
    yaml_file: UploadFile = File(...), secret: str = Form(...), token: str = Form(...)
):
    try:
        # Verify secret and token
        if not secret or not token:
            raise HTTPException(status_code=400, detail="Secret and token are required")

        developer = developer_details_collection.find_one(
            {"secret": secret, "token": token}
        )
        if not developer:
            raise HTTPException(status_code=401, detail="Invalid secret or token")

        # Read and parse YAML data from the uploaded file
        yaml_content = await yaml_file.read()
        yaml_data = yaml.safe_load(yaml_content)

        # Extract company details
        company_id = yaml_data["company"]["company_id"]
        company_name = yaml_data["company"]["name"]
        company_website = yaml_data["company"]["website"]

        # Extract applications and collection points
        applications = yaml_data.get("applications", [])

        inserted_ids = []
        for application in applications:
            application_id = application["application"]["application_id"]
            collection_points = application["application"]["collection_points"]

            for cp in collection_points:
                collection_point_data = cp["collection_point"]
                cp_id = collection_point_data["collection_point_id"]

                # Check if the collection point already exists for the developer
                existing_cp = collection_point_collection.find_one(
                    {
                        "developer_details_id": str(developer["_id"]),
                        "collection_point_id": cp_id,
                    }
                )

                if existing_cp:
                    # Skip insertion if collection point already exists
                    continue

                # Example of extracting data elements
                data_elements = collection_point_data["data_elements"]

                # Example of inserting into MongoDB
                cp_data_to_insert = {
                    "developer_details_id": str(developer["_id"]),
                    "company_id": company_id,
                    "company_name": company_name,
                    "company_website": company_website,
                    "application_id": application_id,
                    "collection_point_id": cp_id,
                    "collection_point_name": collection_point_data["cp_name"],
                    "registered_at": datetime.datetime.utcnow(),
                    "data_elements": data_elements,
                }

                result = collection_point_collection.insert_one(cp_data_to_insert)
                if result.acknowledged:
                    inserted_ids.append(str(result.inserted_id))

        return JSONResponse(
            content={
                "message": f"{len(inserted_ids)} collection points inserted",
                "ids": inserted_ids,
            }
        )

    except Exception as e:
        return JSONResponse(
            content={"message": f"Failed to process request. Error: {str(e)}"},
            status_code=500,
        )

@app.post("/update-collection-point")
async def update_collection_point(
    yaml_file: UploadFile = File(...), secret: str = Form(...), token: str = Form(...)
):
    try:
        # Verify secret and token
        if not secret or not token:
            raise HTTPException(status_code=400, detail="Secret and token are required")

        developer = developer_details_collection.find_one(
            {"secret": secret, "token": token}
        )
        if not developer:
            raise HTTPException(status_code=401, detail="Invalid secret or token")

        # Read and parse YAML data from the uploaded file
        yaml_content = await yaml_file.read()
        yaml_data = yaml.safe_load(yaml_content)

        # Extract company details
        company_id = yaml_data["company"]["company_id"]
        company_name = yaml_data["company"]["name"]
        company_website = yaml_data["company"]["website"]

        # Extract applications and collection points
        applications = yaml_data.get("applications", [])

        updated_ids = []
        for application in applications:
            application_id = application["application"]["application_id"]
            collection_points = application["application"]["collection_points"]

            for cp in collection_points:
                collection_point_data = cp["collection_point"]
                cp_id = collection_point_data["collection_point_id"]

                # Check if the collection point exists for the developer
                existing_cp = collection_point_collection.find_one(
                    {
                        "developer_details_id": str(developer["_id"]),
                        "collection_point_id": cp_id,
                    }
                )

                if existing_cp:
                    # Update the existing collection point
                    update_data = {
                        "company_id": company_id,
                        "company_name": company_name,
                        "company_website": company_website,
                        "application_id": application_id,
                        "collection_point_name": collection_point_data["cp_name"],
                        "registered_at": datetime.datetime.utcnow(),
                        "data_elements": collection_point_data["data_elements"],
                    }

                    result = collection_point_collection.update_one(
                        {"_id": existing_cp["_id"]},
                        {"$set": update_data}
                    )

                    if result.modified_count > 0:
                        updated_ids.append(str(existing_cp["_id"]))

        return JSONResponse(
            content={
                "message": f"{len(updated_ids)} collection points updated",
                "ids": updated_ids,
            }
        )

    except Exception as e:
        return JSONResponse(
            content={"message": f"Failed to process request. Error: {str(e)}"},
            status_code=500,
        )

@app.get("/get-collection-points")
async def get_collection_points(secret: str, token: str):
    try:
        # Verify the secret and token against your developer details collection
        developer = developer_details_collection.find_one(
            {"secret": secret, "token": token}
        )
        if not developer:
            raise HTTPException(status_code=401, detail="Invalid secret or token")

        # Fetch collection points for the authenticated user
        collection_points = []
        cursor = collection_point_collection.find(
            {"developer_details_id": str(developer["_id"])}
        )

        for document in cursor:
            # Convert ObjectId to string for serialization
            document["_id"] = str(document["_id"])
            collection_points.append(document)

        return collection_points

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch collection points. Error: {str(e)}",
        )
