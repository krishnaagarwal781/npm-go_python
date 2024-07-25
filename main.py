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


class Purpose(BaseModel):
    purpose_description: str
    purpose_language: str


class DataElement(BaseModel):
    data_element: str
    data_element_title: str
    data_element_description: str
    data_owner: str
    legal_basis: str
    retention_period: str
    expiry: str
    purposes: List[Purpose]


class CollectionPointRequest(BaseModel):
    org_id: str
    org_key: str
    org_secret: str
    application_id: str
    cp_name: str
    cp_url: str
    data_elements: List[DataElement]


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
db = client["python-go2"]
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


@app.get("/")
async def read_root():
    return {"message": "Welcome bhidu"}


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

    # Prepare collection point data from the request for database insertion
    collection_point_data = {
        "org_id": data.org_id,
        "application_id": data.application_id,
        "cp_name": data.cp_name,
        "cp_status": "active",
        "cp_url": data.cp_url,
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

    # Insert the collection point data into MongoDB
    cp_result = collection_point_collection.insert_one(collection_point_data)
    if not cp_result.acknowledged:
        raise HTTPException(
            status_code=500, detail="Failed to insert collection point details"
        )

    # Retrieve the inserted cp_id
    cp_id = str(cp_result.inserted_id)

    # Prepare response data by removing purpose_id and other fields
    response_data = {
        "cp_id": cp_id,
        "cp_name": data.cp_name,
        "cp_status": "active",
        "cp_url": data.cp_url,
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


@app.get("/get-notice-info/{cp_id}")
async def get_notice_info(
    cp_id: str, app_id: str, org_id: str, org_key: str, org_secret: str
):
    # Verify org_key and org_secret
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    # Retrieve collection point for the given cp_id, org_id, and app_id
    collection_point = collection_point_collection.find_one(
        {"_id": ObjectId(cp_id), "org_id": org_id, "application_id": app_id}
    )

    if not collection_point:
        raise HTTPException(
            status_code=404, detail=f"Collection point with ID {cp_id} not found"
        )

    # Construct notice_info response for the specific collection point
    notice_info = {
        "urls": {
            "logo": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTI2K4cwj_yTWk-rSebFdFF-tX1yMKE8o_Uwnk5H9GYkIoqSKHAvt-pYaB1dEQHK1paNNk&usqp=CAU",
            "speakIcon": "https://www.svgrepo.com/show/165176/speaking.svg",
            "pauseIcon": "https://www.svgrepo.com/show/149256/pause-button.svg",
            "arrowIcon": "https://cdn.icon-icons.com/icons2/2248/PNG/512/arrow_top_right_icon_135926.png",
            "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
            "dpar_link": "https://www.instagram.com",
            "manage_consent_link": "https://www.facebook.com",
        },
        "english": {
            "collection_point": {},
            "meta_data": {
                "header": "Consent Notice",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "Digital Personal Data Protection Act 2023",
                "description": "An Act to provide for the processing of digital personal data in a manner that recognises both the right of individuals to protect their personal data and theneed to process such personal data for lawful purposes and for matters connected therewith or incidental thereto",
                "manage_consent_title": "Manage Consent Preferences",
            },
            "button": {
                "primary": "Accept",
                "secondary": "Cancel",
                "selectAll": "Select All",
            },
        },
        "hindi": {
            "collection_point": {},
            "meta_data": {
                "header": "डेटा सहमति सूचना",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023",
                "description": "डिजिटल व्यक्तिगत डेटा के प्रसंस्करण के लिए इस तरह से प्रावधान करने के लिए एक अधिनियम जो व्यक्तियों के अपने व्यक्तिगत डेटा की सुरक्षा के अधिकार और कानूनी उद्देश्यों के लिए ऐसे व्यक्तिगत डेटा को संसाधित करने की आवश्यकता और उससे जुड़े या उसके प्रासंगिक मामलों को मान्यता देता है।",
                "manage_consent_title": "सहमति प्राथमिकताएँ प्रबंधित करें",
            },
            "button": {
                "primary": "स्वीकार",
                "secondary": "रद्द",
                "selectAll": "सबका चयन करें",
            },
        },
        "tamil": {
            "collection_point": {},
            "meta_data": {
                "header": "ஒப்புதல் அறிவிப்பு",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "டிஜிட்டல் தனிப்பட்ட தரவுகளை பாதுகாப்பு சட்டம் 2023",
                "description": "நபர்களின் தனிப்பட்ட தரவுகளை பாதுகாக்கும் உரிமையை மற்றும் சட்டப்பூர்வமான நோக்கங்களுக்காக அவ்வாறு தனிப்பட்ட தரவுகளை செயலாக்கும் தேவையை கௌரவிக்கும் வகையில் டிஜிட்டல் தனிப்பட்ட தரவுகளை செயலாக்குவதற்கான ஒரு சட்டம் மற்றும் அதனுடன் தொடர்புடைய அல்லது உச்சிகாவியவற்றை சார்ந்த விவகாரங்களுக்கான ஒரு சட்டம்",
                "manage_consent_title": "ஒப்புதல் முன்னுரிமைகளை நிர்வகிக்கவும்",
            },
            "button": {
                "primary": "ஏற்றுக்கொள்",
                "secondary": "ரத்து",
                "selectAll": "அனைத்தையும் தேர்வுசெய்க",
            },
        },
        "telugu": {
            "collection_point": {},
            "meta_data": {
                "header": "సమ్మతి నోటీసు",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "డిజిటల్ వ్యక్తిగత డేటా రక్షణ చట్టం 2023",
                "description": "వ్యక్తుల వ్యక్తిగత డేటా రక్షణ హక్కును మరియు చట్టబద్ధమైన ఉద్దేశ్యాల కోసం ఆ డేటాను ప్రాసెస్ చేయడానికి అవసరాన్ని గుర్తించేవిధంగా డిజిటల్ వ్యక్తిగత డేటా ప్రాసెసింగ్ కోసం ఒక చట్టం మరియు దానికి సంబంధించిన లేదా అనుబంధ విషయాల కోసం",
                "manage_consent_title": "సమ్మతి ప్రాధాన్యతలను నిర్వహించండి",
            },
            "button": {
                "primary": "అంగీకరించు",
                "secondary": "రద్దు చేయి",
                "selectAll": "అన్నీ ఎంచుకో",
            },
        },
        "gujarati": {
            "collection_point": {},
            "meta_data": {
                "header": "મંજુરી સૂચના",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "ડિજિટલ વ્યક્તિગત ડેટા સુરક્ષા અધિનિયમ 2023",
                "description": "વ્યક્તિઓના વ્યક્તિગત ડેટાને સુરક્ષિત રાખવા હક્ક અને કાનૂની હેતુઓ માટે આવા ડેટાના પ્રોસેસિંગની જરૂરિયાત બંનેને માન્યતા આપતી રીતે ડિજિટલ વ્યક્તિગત ડેટાના પ્રોસેસિંગ માટેનો એક અધિનિયમ અને તેનાથી જોડાયેલા અથવા સબંધિત બાબતો માટે",
                "manage_consent_title": "મંજુરી પસંદગીઓ મેનેજ કરો",
            },
            "button": {
                "primary": "સ્વીકારો",
                "secondary": "રદ કરો",
                "selectAll": "બધા પસંદ કરો",
            },
        },
        "assamese": {
            "collection_point": {},
            "meta_data": {
                "header": "সম্মতি সূচনা",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "ডিজিটেল ব্যক্তিগত তথ্য সুৰক্ষা আইন 2023",
                "description": "ব্যক্তিৰ ব্যক্তিগত তথ্য সুৰক্ষাৰ অধিকাৰ আৰু আইনানুগ উদ্দেশ্যৰ বাবে সেই ব্যক্তিগত তথ্য প্ৰসেশন কৰিবলৈ প্ৰয়োজনীয়তাক মান্যতা দিয়াৰ কাৰণে ডিজিটেল ব্যক্তিগত তথ্য প্ৰসেশনৰ ব্যৱস্থা কৰিবলৈ এক আইন আৰু তাৰ সৈতে সম্পৰ্কিত বা আনুষঙ্গিক বিষয়ৰ বাবে এক আইন",
                "manage_consent_title": "সম্মতি পছন্দসমূহ পৰিচালনা কৰক",
            },
            "button": {
                "primary": "গ্ৰহণ কৰক",
                "secondary": "বাতিল কৰক",
                "selectAll": "সকলো বাছক",
            },
        },
        "bengali": {
            "collection_point": {},
            "meta_data": {
                "header": "সম্মতি নোটিশ",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "ডিজিটাল ব্যক্তিগত তথ্য সুরক্ষা আইন 2023",
                "description": "একটি আইন যা ব্যক্তিরা তাদের ব্যক্তিগত তথ্য সুরক্ষার অধিকার এবং এই ধরনের ব্যক্তিগত তথ্য আইনগত উদ্দেশ্যে প্রক্রিয়া করার প্রয়োজনীয়তা উভয়কেই স্বীকৃতি দেয়, ডিজিটাল ব্যক্তিগত তথ্য প্রক্রিয়া করার জন্য এবং এর সাথে সম্পর্কিত বা আনুষঙ্গিক বিষয়ে একটি আইন",
                "manage_consent_title": "সম্মতি পছন্দগুলি পরিচালনা করুন",
            },
            "button": {
                "primary": "গ্রহণ করুন",
                "secondary": "বাতিল করুন",
                "selectAll": "সবগুলি নির্বাচন করুন",
            },
        },
        "bodo": {
            "collection_point": {},
            "meta_data": {
                "header": "अनुमति बिजेनाय",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "डिजिटल व्यक्तिगत डेटा रक्षा ऐन 2023",
                "description": "दखालोंगुं आपन व्यक्तिगत डेटा सुरुखो अरथ बिसारवाव अर कानूनी उद्देश्य नाय दादखाल किया होओ बिसारवाव ददरखाय माने ओसोर डाटानाय प्रोससिंग करव फालंगुं बिसार होओ एक ऐन अर हेगोगोनाय संबधि ओसोर या उडातै बिजें नाय एक ऐन",
                "manage_consent_title": "अनुमति प्रायोरिटिज मोजैनाव",
            },
            "button": {
                "primary": "आसरा",
                "secondary": "खतमाव",
                "selectAll": "सब ओनाय चुनाव",
            },
        },
        "dogri": {
            "collection_point": {},
            "meta_data": {
                "header": "सहमति सूचना",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023",
                "description": "डिजिटल व्यक्तिगत डेटा दे प्रोसेसिंग दे लई इक क़ानून जो की व्यक्तियों दे व्यक्तिगत डेटा दे संरक्षण दे अधिकार अते ऐसे व्यक्तिगत डेटा नू क़ानूनी मकसदां दे लई प्रोसेस करन दी लोड नू मान्यता दिन्दा है, अते उसनाल जुड़े होए या उस दे होर मामले लई",
                "manage_consent_title": "सहमति प्राथमिकतावाँ प्रबंधित करो",
            },
            "button": {
                "primary": "स्वीकारो",
                "secondary": "रद्द करो",
                "selectAll": "सारे चूनो",
            },
        },
        "kashmiri": {
            "collection_point": {},
            "meta_data": {
                "header": "رضایت نامہ",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "ڈیجیٹل پرسنل ڈیٹا پروٹیکشن ایکٹ 2023",
                "description": "ایک ایسا قانون جو افراد کے ذاتی ڈیٹا کے تحفظ کے حق اور اس طرح کے ذاتی ڈیٹا کو قانونی مقاصد کے لیے پروسیس کرنے کی ضرورت دونوں کو تسلیم کرتا ہے، ڈیجیٹل ذاتی ڈیٹا پروسیسنگ کے لیے اور اس سے متعلقہ یا اس سے متعلق معاملات کے لیے",
                "manage_consent_title": "رضامندی کی ترجیحات کا نظم کریں",
            },
            "button": {
                "primary": "قبول کریں",
                "secondary": "منسوخ کریں",
                "selectAll": "سبھی کا انتخاب کریں",
            },
        },
    }

    # Populate collection point data in notice_info
    data_elements = []
    for de in collection_point.get("data_elements", []):
        purposes = []
        for purpose in de.get("purposes", []):
            purposes.append(
                {
                    "purpose_description": purpose.get("purpose_description", ""),
                    "purpose_language": purpose.get("purpose_language", ""),
                }
            )
        data_elements.append(
            {
                "data_element": de.get("data_element", ""),
                "data_element_title": de.get("data_element_title", ""),
                "data_element_description": de.get("data_element_description", ""),
                "data_owner": de.get("data_owner", ""),
                "legal_basis": de.get("legal_basis", ""),
                "retention_period": de.get("retention_period", ""),
                "cross_border": de.get("cross_border", False),
                "sensitive": de.get("sensitive", False),
                "encrypted": de.get("encrypted", False),
                "expiry": de.get("expiry", ""),
                "purposes": purposes,
            }
        )

    collection_point_info = {
        "cp_id": str(collection_point["_id"]),
        "cp_name": collection_point.get("cp_name", ""),
        "cp_status": collection_point.get("cp_status", ""),
        "cp_url": collection_point.get("cp_url", ""),
        "data_elements": data_elements,
    }

    notice_info["english"]["collection_point"] = collection_point_info
    notice_info["hindi"]["collection_point"] = collection_point_info
    notice_info["tamil"]["collection_point"] = collection_point_info
    notice_info["telugu"]["collection_point"] = collection_point_info
    notice_info["gujarati"]["collection_point"] = collection_point_info
    notice_info["assamese"]["collection_point"] = collection_point_info
    notice_info["bengali"]["collection_point"] = collection_point_info
    notice_info["bodo"]["collection_point"] = collection_point_info
    notice_info["dogri"]["collection_point"] = collection_point_info
    notice_info["kashmiri"]["collection_point"] = collection_point_info

    return {"notice_info": notice_info}
