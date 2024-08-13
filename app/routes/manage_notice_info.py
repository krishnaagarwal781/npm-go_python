from fastapi import FastAPI, HTTPException, Header, APIRouter, Request
from fastapi.responses import JSONResponse
from app.config.db import (
    collection_point_collection,
    developer_details_collection,
    static_notice_data,
)
from bson import ObjectId
from datetime import datetime
import secrets
from slowapi import Limiter
from slowapi.util import get_remote_address
from limits.storage import RedisStorage

# Initialize RedisStorage and Limiter
redis_url = "redis://default:GtOhsmeCwPJsZC8B0A8R2ihcA7pDVXem@redis-11722.c44.us-east-1-2.ec2.cloud.redislabs.com:11722/0"  # Adjust the Redis URL as needed
storage = RedisStorage(redis_url)
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)

noticeRouter = APIRouter()


@noticeRouter.get("/get-notice-info", tags=["Notice Info"])
@limiter.limit("5/minute")
async def get_notice_info(
    request: Request,
    cp_id: str = Header(...),
    app_id: str = Header(...),
    org_id: str = Header(...),
    org_key: str = Header(...),
    org_secret: str = Header(...),
):
    # Verify the organization
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    # Retrieve the collection point information
    collection_point = collection_point_collection.find_one(
        {"_id": ObjectId(cp_id), "org_id": org_id, "application_id": app_id}
    )
    if not collection_point:
        raise HTTPException(
            status_code=404, detail=f"Collection point with ID {cp_id} not found"
        )

    # Initialize notice_info with URLs
    notice_info = {
        "urls": {
            "logo": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTI2K4cwj_yTWk-rSebFdFF-tX1yMKE8o_Uwnk5H9GYkIoqSKHAvt-pYaB1dEQHK1paNNk&usqp=CAU",
            "speakIcon": "https://www.svgrepo.com/show/165176/speaking.svg",
            "pauseIcon": "https://www.svgrepo.com/show/149256/pause-button.svg",
            "arrowIcon": "https://cdn.icon-icons.com/icons2/2248/PNG/512/arrow_top_right_icon_135926.png",
            "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
            "dpar_link": "https://privacy-center.vercel.app/dparwebform",
            "manage_consent_link": "http://localhost:3000/manage-consent",
        }
    }

    # Fetch all static_notice_data documents
    static_notice_data_docs = list(static_notice_data.find({}))

    # Update notice_info with the languages and their data
    for doc in static_notice_data_docs:
        for lang_key, lang_data in doc.items():
            if lang_key not in [
                "_id",
                "lang_short_code",
                "lang_display",
                "lang_title",
                "lang_639_2_code",
                "translation_symbol",
            ]:
                notice_info[lang_key] = {
                    "collection_point": {},
                    "meta_data": lang_data.get("meta_data", {}),
                    "button": lang_data.get("button", {}),
                    "lang_title": doc.get("lang_title", ""),
                    "lang_display": doc.get("lang_display", ""),
                    "lang_short_code": doc.get("lang_short_code", ""),
                }

    # Add collection point data to each language
    data_elements = []
    for de in collection_point.get("data_elements", []):
        purposes = []
        for purpose in de.get("purposes", []):
            purposes.append(
                {
                    "purpose_id": purpose.get("purpose_id", ""),
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

    # Update notice_info with collection_point_info for each language
    for lang_key in notice_info.keys():
        if lang_key != "urls":
            notice_info[lang_key]["collection_point"] = collection_point_info

    return {"notice_info": notice_info}
