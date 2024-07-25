package models

import "time"

// Config represents the configuration structure.
type Config struct {
	MongoDBURI string        
	LogLevel   string
	Dbname	 string        
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





type CollectionPointData struct {
	Id		 string         `bson:"_id,omitempty" json:"id" yaml:"id"`
	OrgID      string         `bson:"org_id" json:"org_id" yaml:"org_id"`
	AppID      string         `bson:"app_id" json:"application_id" yaml:"application_id"`
	CPName     string         `bson:"cp_name" json:"cp_name" yaml:"cp_name"`
	CPStatus   string         `bson:"cp_status" json:"cp_status" yaml:"cp_status"`
	CPURL      string         `bson:"cp_url" json:"cp_url" yaml:"cp_url"`
	DataElements []DataElement `bson:"data_elements" json:"data_elements" yaml:"data_elements"`
}

type DataElement struct {
	DataElement                 string     `bson:"data_element" json:"data_element" yaml:"data_element"`
	DataElementTitle            string     `bson:"data_element_title" json:"data_element_title" yaml:"data_element_title"`
	DataElementDescription      string     `bson:"data_element_description" json:"data_element_description" yaml:"data_element_description"`
	DataOwner                   string     `bson:"data_owner" json:"data_owner" yaml:"data_owner"`
	LegalBasis                  string     `bson:"legal_basis" json:"legal_basis" yaml:"legal_basis"`
	RetentionPeriod             string     `bson:"retention_period" json:"retention_period" yaml:"retention_period"`
	CrossBorder                 bool       `bson:"cross_border" json:"cross_border" yaml:"cross_border"`
	Sensitive                   bool       `bson:"sensitive" json:"sensitive" yaml:"sensitive"`
	Encrypted                   bool       `bson:"encrypted" json:"encrypted" yaml:"encrypted"`
	Expiry                      string     `bson:"expiry" json:"expiry" yaml:"expiry"`
	DataElementCollectionStatus string     `bson:"data_element_collection_status" json:"data_element_collection_status" yaml:"data_element_collection_status"`
	Purposes                    []Purpose  `bson:"purposes" json:"purposes" yaml:"purposes"`
	Registered_at			   time.Time  `bson:"registered_at" json:"registered_at" yaml:"registered_at"`
}

type Purpose struct {
	PurposeID          string `bson:"purpose_id" json:"purpose_id" yaml:"purpose_id"`
	PurposeDescription string `bson:"purpose_description" json:"purpose_description" yaml:"purpose_description"`
	PurposeLanguage    string `bson:"purpose_language" json:"purpose_language" yaml:"purpose_language"`
}






// YamlTemplate represents the top-level structure in the YAML file
type YamlTemplate struct {
	Version      string        `yaml:"version"`
	Applications []Application `yaml:"applications"`
	Company	  Company       `yaml:"company"`

}


// Application represents the application structure in the YAML file
type Application struct {
	ApplicationID    string   `yaml:"application_id"`
	Type	string   `yaml:"type"`
	CollectionPoints []CollectionPointData `yaml:"collection_points"`
}

type Company struct{
	CompanyID string `json:"company_id" bson:"company_id" yaml:"company_id"`
	CompanyName string `json:"name" bson:"name" yaml:"name"`
	CompanyWebsite string `json:"website" bson:"website" yaml:"website"`
}




type CollectionPointRequest struct {
	OrgID string `json:"org_id"`
	AppID string `json:"app_id"`
	OrganisationKey string `json:"org_key"`
	OrganisationSecret string `json:"org_secret"`
}