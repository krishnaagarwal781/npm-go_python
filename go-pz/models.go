package main

type DeveloperDetails struct {
	DeveloperEmail   string `json:"developer_email"`
	DeveloperWebsite string `json:"developer_website"`
	DeveloperCity    string `json:"developer_city"`
	DeveloperMobile  string `json:"developer_mobile"`
	OrganisationName string `json:"organisation_name"`
}

type OrganisationDetails struct {
	OrganisationName string `json:"organisation_name"`
	DeveloperEmail   string `json:"developer_email"`
}

type CollectionPointRequest struct {
	Secret string `json:"secret"`
	Token  string `json:"token"`
}
type CollectionPointUpdateRequest struct {
	Secret   string `json:"secret"`
	Token    string `json:"token"`
	CpID     string `json:"cp_id"`
	CpName   string `json:"cp_name"`
	CpURL    string `json:"cp_url"`
	CpStatus string `json:"cp_status"`
}

type CollectionPoint struct {
	CollectionPointID string        `json:"collection_point_id"`
	CpName            string        `json:"cp_name"`
	CpURL             string        `json:"cp_url"`
	CpStatus          string        `json:"cp_status"`
	DataElements      []DataElement `json:"data_elements"`
}

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

type Purpose struct {
	PurposeID          string `json:"purpose_id"`
	PurposeDescription string `json:"purpose_description"`
	PurposeLanguage    string `json:"purpose_language"`
}
