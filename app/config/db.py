from pymongo import MongoClient

client = MongoClient(
    "mongodb://gewgawrav:catax1234@concur.cumulate.live"
)
db = client["python-sdk"]
developer_details_collection = db["developer_details"]
organisation_collection = db["organisation_details"]
application_collection = db["org_applications"]
collection_point_collection = db["collection_points"]
consent_preferences_collection = db["consent_preferences"]
user_consent_headers = db["user_consent_headers"]
static_notice_data = db["static_notice_data"]

translated_data_element_collection = client["Concur_Backend_New"]["translated_data_elements"]

consent_directory_collection = client['Consent_directory_db']['consent_directory_new_krishna']

consent_directory_languages_collection = client['Consent_directory_db']['consent_language']