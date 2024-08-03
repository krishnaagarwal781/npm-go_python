from pydantic import BaseModel
from typing import List, Dict, Optional


class DeveloperDetails(BaseModel):
    developer_email: str
    developer_website: str
    developer_mobile: str
    organisation_name: str
    contact_consent: bool


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
    data_owner: List[str]
    legal_basis: str
    retention_period: int
    expiry: int
    purposes: List[Purpose]


class CollectionPointRequest(BaseModel):
    cp_name: str
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


class LinkedInAgreement(BaseModel):
    method: str
    agreement: str

class ConsentDetail(BaseModel):
    purpose_id: str
    consent_status: str
    shared: bool
    data_processors: List[str] = []
    cross_border: bool
    consent_timestamp: str
    expiry_date: str
    retention_date: str

class DataElement(BaseModel):
    data_element: str
    consents: List[ConsentDetail]

class ConsentPreferenceBody(BaseModel):
    consent_language: str
    linkedin_agreement: LinkedInAgreement
    data_elements: List[DataElement]