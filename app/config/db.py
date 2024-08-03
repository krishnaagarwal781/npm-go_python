from pymongo import MongoClient

client = MongoClient(
    "mongodb+srv://sniplyuser:NXy7R7wRskSrk3F2@cataxprod.iwac6oj.mongodb.net/?retryWrites=true&w=majority"
)
db = client["python-go3"]
developer_details_collection = db["developer_details"]
organisation_collection = db["organisation_details"]
application_collection = db["org_applications"]
collection_point_collection = db["collection_points"]
consent_preferences_collection = db["consent_preferences"]
user_consent_headers = db["user_consent_headers"]