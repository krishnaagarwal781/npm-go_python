package main

import (
	"math/rand"
	"strings"
)

func GenerateSecret(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	var secret strings.Builder
	for i := 0; i < length; i++ {
		secret.WriteByte(charset[rand.Intn(len(charset))])
	}
	return secret.String()
}

func GenerateToken(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
	var token strings.Builder
	for i := 0; i < length; i++ {
		token.WriteByte(charset[rand.Intn(len(charset))])
	}
	return token.String()
}

func CreateYAMLTemplate(developer map[string]interface{}) string {
	// Create YAML template based on developer data
	// Example implementation
	// Replace with your YAML structure and data
	yamlTemplate := `
version: "1.0"
company:
  name: Your Company Name
  website: https://www.yourcompanywebsite.com
  company_id: 12345
applications:
  - application:
      application_id: app1
      type: Mobile
      collection_points:
        - collection_point:
            collection_point_id: cp1
            cp_name: Collection Point 1
            cp_url: https://www.collectionpoint1.com
            cp_status: active
            data_elements:
              - data_element: home_address
                data_element_title: Home Address
                data_element_description: One line description of home address field
                data_element_collection_status: active
                expiry: 90 days
                cross_border: false
                data_principal: false
                sensitive: true
                encrypted: true
                retention_period: 5 years
                data_owner: Customer Service Department
                legal_basis: Consent
                purposes:
                  - purpose_id: p1
                    purpose_description: Purpose description for home address
                    purpose_language: EN
                  - purpose_id: p2
                    purpose_description: Another purpose for home address
                    purpose_language: EN
        - collection_point:
            collection_point_id: cp2
            cp_name: Collection Point 2
            cp_url: https://www.collectionpoint2.com
            cp_status: active
            data_elements:
              - data_element: email_address
                data_element_title: Email Address
                data_element_description: One line description of email address field
                data_element_collection_status: active
                expiry: 30 days
                cross_border: true
                data_principal: true
                sensitive: false
                encrypted: true
                retention_period: 2 years
                data_owner: Sales Department
                legal_basis: Contractual Necessity
                purposes:
                  - purpose_id: p3
                    purpose_description: Purpose description for email address
                    purpose_language: EN
                  - purpose_id: p4
                    purpose_description: Another purpose for email address
                    purpose_language: EN
`
	return yamlTemplate
}
