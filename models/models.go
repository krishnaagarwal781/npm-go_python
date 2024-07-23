package models

// DeveloperDetails represents developer registration data.
type DeveloperDetails struct {
	DeveloperEmail   string `json:"developer_email"`
	DeveloperWebsite string `json:"developer_website"`
	DeveloperCity    string `json:"developer_city"`
	DeveloperMobile  string `json:"developer_mobile"`
	OrganisationName string `json:"organisation_name"`
}

// CollectionPointRequest represents request data for creating a collection point.
type CollectionPointRequest struct {
	Secret string `json:"secret"`
	Token  string `json:"token"`
}

// CollectionPoint represents data structure for a collection point.
type CollectionPoint struct {
	CollectionPointID     string        `json:"collection_point_id"`
	CollectionPointName   string        `json:"cp_name"`
	CollectionPointURL    string        `json:"cp_url"`
	CollectionPointStatus string        `json:"cp_status"`
	DataElements          []DataElement `json:"data_elements"`
}

// DataElement represents data element details.
type DataElement struct {
	DataElement                 string    `json:"data_element"`
	DataElementTitle            string    `json:"data_element_title"`
	DataElementDescription      string    `json:"data_element_description"`
	DataElementCollectionStatus string    `json:"data_element_collection_status"`
	Expiry                      string    `json:"expiry"`
	CrossBorder                 bool      `json:"cross_border"`
	DataPrincipal               bool      `json:"data_principal"`
	Sensitive                   bool      `json:"sensitive"`
	Encrypted                   bool      `json:"encrypted"`
	RetentionPeriod             string    `json:"retention_period"`
	DataOwner                   string    `json:"data_owner"`
	LegalBasis                  string    `json:"legal_basis"`
	Purposes                    []Purpose `json:"purposes"`
}

// Purpose represents purpose details for data collection.
type Purpose struct {
	PurposeID          string `json:"purpose_id"`
	PurposeDescription string `json:"purpose_description"`
	PurposeLanguage    string `json:"purpose_language"`
}


// Config represents the configuration structure.
type Config struct {
	MongoDBURI string        
	LogLevel   string
	Dbname	 string        
}