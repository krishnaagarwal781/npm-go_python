from pymongo import MongoClient

client = MongoClient(
    "mongodb+srv://concur-admin:oApIL0eGKTzHeWrn@concur-backend-db.3jzk7uh.mongodb.net"
)
db = client["python-sdk"]
developer_details_collection = db["developer_details"]
organisation_collection = db["organisation_details"]
application_collection = db["org_applications"]
collection_point_collection = db["collection_points"]
consent_preferences_collection = db["consent_preferences"]
user_consent_headers = db["user_consent_headers"]
