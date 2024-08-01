package models

import "time"

// Config represents the configuration structure.
type Config struct {
	MongoDBURI string        
	LogLevel   string
	Dbname	 string
	Port string        
}

type OrganisationDetails struct {
	Id string `json:"id" bson:"_id,omitempty"`
	OrganisationName string `json:"organisation_name" bson:"organisation_name"`
	DeveloperEmail   string `json:"developer_email" bson:"developer_email"`
	Developer_details_id string `json:"developer_details_id" bson:"developer_details_id" `
	Registered_at	time.Time `json:"registered_at" bson:"registered_at"`
}

// DeveloperDetails represents developer registration data.
type DeveloperDetails struct {
	Id string `json:"id" bson:"_id,omitempty"`
	DeveloperEmail   string `json:"developer_email" bson:"developer_email"`
	DeveloperWebsite string `json:"developer_website" bson:"developer_website"`
	DeveloperCity    string `json:"developer_city" bson:"developer_city"`
	DeveloperMobile  string `json:"developer_mobile" bson:"developer_mobile"`
	OrganisationName string `json:"organisation_name" bson:"organisation_name"`
	OrganisationKey  string `json:"org_key" bson:"org_key"`
	OrganisationSecret string `json:"org_secret" bson:"org_secret"`
	Registered_at	time.Time `json:"registered_at" bson:"registered_at"`
	OrganisationID string `json:"organisation_id" bson:"organisation_id"`
	Headers map[string]string `json:"headers" bson:"headers"`
	ClientIP string `json:"client_ip" bson:"client_ip"`
}





// ApplicationDetails represents application registration data.
type ApplicationDetails struct {
	Id string `json:"id" bson:"_id,omitempty"`
	AppType         string `json:"app_type" bson:"app_type"`
	AppName         string `json:"app_name" bson:"app_name"`
	AppStage        string `json:"app_stage" bson:"app_stage"`
	ApplicationUser string `json:"application_user" bson:"application_user"`
	OrganisationID  string `json:"org_id" bson:"org_id"`
	ApplicationID   string `json:"app_id" bson:"app_id"`
	Registered_at	time.Time `json:"registered_at" bson:"registered_at"`

}


type ApplicationResponse struct {
	YamlData YamlTemplate `json:"yaml_data"`
	Con_app_id string `json:"con_app_id"`
	App_type string `json:"app_type"`
	App_name string `json:"app_name"`
	App_stage string `json:"app_stage"`
	Application_user string `json:"application_user"`
}


// YamlTemplate represents the top-level structure in the YAML file
type YamlTemplate struct {
	Version      string        `yaml:"version" json:"version"`
	OrganisationID string `yaml:"organisation_id" json:"organisation_id"`
	Applications []Application `yaml:"applications" json:"applications"`
}


// Application represents the application structure in the YAML file
type Application struct {
	ApplicationID    string   `yaml:"application_id" json:"application_id"`
	Type	string   `yaml:"type" json:"type"`
	Name   string   `yaml:"name" json:"name"`
	Stage  string   `yaml:"stage" json:"stage"`
	ApplicationUser string `yaml:"application_user" json:"application_user"`
	CollectionPoints []CollectionPointData `yaml:"collection_points_data" json:"collection_points_data"`
}



type CollectionPointData struct {
	Id		 string         `bson:"_id,omitempty" json:"cp_id" yaml:"cp_id"`
	CPName     string         `bson:"cp_name" json:"cp_name" yaml:"cp_name"`
	CPStatus   string         `bson:"cp_status" json:"cp_status" yaml:"cp_status" default:"active"`
	CPURL      string         `bson:"cp_url" json:"cp_url" yaml:"cp_url"`
	DataElements []DataElement `bson:"data_elements" json:"data_elements" yaml:"data_elements"`
}

type DataElement struct {
	DataElement                 string     `bson:"data_element" json:"data_element" yaml:"data_element"`
	DataElementCollectionStatus string     `bson:"data_element_collection_status" json:"data_element_collection_status" yaml:"data_element_collection_status"`
	DataElementTitle            string     `bson:"data_element_title" json:"data_element_title" yaml:"data_element_title"`
	DataElementDescription      string     `bson:"data_element_description" json:"data_element_description" yaml:"data_element_description"`
	DataOwner                   []string     `bson:"data_owner" json:"data_owner" yaml:"data_owner"`
	LegalBasis                  string     `bson:"legal_basis" json:"legal_basis" yaml:"legal_basis"`
	RetentionPeriod             int32     `bson:"retention_period" json:"retention_period" yaml:"retention_period"`
	CrossBorder                 bool       `bson:"cross_border" json:"cross_border" yaml:"cross_border"`
	Sensitive                   bool       `bson:"sensitive" json:"sensitive" yaml:"sensitive"`
	Encrypted                   bool       `bson:"encrypted" json:"encrypted" yaml:"encrypted"`
	Expiry                      int32     `bson:"expiry" json:"expiry" yaml:"expiry"`
	
	Purposes                    []Purpose  `bson:"purposes" json:"purposes" yaml:"purposes"`
}

type Purpose struct {
	PurposeID          string `bson:"purpose_id" json:"purpose_id" yaml:"purpose_id"`
	PurposeDescription string `bson:"purpose_description" json:"purpose_description" yaml:"purpose_description"`
	PurposeLanguage    string `bson:"purpose_language" json:"purpose_language" yaml:"purpose_language"`
}





type CollectionPointRequest struct {
	OrgID string `json:"org_id"`
	AppID string `json:"application_id"`
	OrganisationKey string `json:"org_key"`
	OrganisationSecret string `json:"org_secret"`
	CollectionPointName string `json:"cp_name"`
	DataElements []DataElement `json:"data_elements"`
}

type CollectionPointResponse struct {
	Message string `json:"message"`
	CollectionPointData CollectionPointData `json:"collection_point_data"`
}

type YamlUpdateResponse struct {
	Message string `json:"message"`
	YamlData YamlTemplate `json:"yaml_data"`
}

type GetCollectionPointsResponse struct {
	CollectionPoints []CollectionPointData `json:"con_collection_points"`
}



type ConsentPreferenceRequest struct {
    OrgID        string          `json:"org_id"`
    OrgKey       string          `json:"org_key"`
    OrgSecret    string          `json:"org_secret"`
    CPID         string          `json:"cp_id"`
    DPID         string          `json:"dp_id"`
    ConsentScope []ConsentScope  `json:"consent_scope"`
}

type ConsentScope struct {
    DataElementName string `json:"data_element_name"`
    PurposeID       string `json:"purpose_id"`
    ConsentStatus   string `json:"consent_status"`
    Shared          bool   `json:"shared"`
    DataProcessorID []string `json:"data_processor_id"`
    CrossBorder     bool   `json:"cross_border"`
}

type PostConsentPreferenceResponse struct {
    Message    string `json:"message"`
    AgreementID string `json:"agreement_id"`
}