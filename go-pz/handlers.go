package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

func PackageRegisterHandler(w http.ResponseWriter, r *http.Request) {
	var data DeveloperDetails
	err := json.NewDecoder(r.Body).Decode(&data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Generate secret and token
	secret := GenerateSecret(16)
	token := GenerateToken(32)

	// Prepare developer data
	developerData := map[string]interface{}{
		"developer_email":   data.DeveloperEmail,
		"developer_website": data.DeveloperWebsite,
		"developer_city":    data.DeveloperCity,
		"developer_mobile":  data.DeveloperMobile,
		"organisation_name": data.OrganisationName,
		"secret":            secret,
		"token":             token,
		"registered_at":     time.Now().UTC(),
	}

	// Insert into MongoDB
	err = InsertDeveloperDetails(developerData)
	if err != nil {
		http.Error(w, "Failed to insert developer details", http.StatusInternalServerError)
		return
	}

	// Insert into organisation collection
	err = InsertOrganisationDetails(data.OrganisationName, data.DeveloperEmail, secret)
	if err != nil {
		http.Error(w, "Failed to insert organisation details", http.StatusInternalServerError)
		return
	}

	// Return secret and token
	response := map[string]string{
		"secret": secret,
		"token":  token,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func CreateCollectionPointHandler(w http.ResponseWriter, r *http.Request) {
	var data CollectionPointRequest
	err := json.NewDecoder(r.Body).Decode(&data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Verify secret and token
	developer, err := VerifyDeveloper(data.Secret, data.Token)
	if err != nil {
		http.Error(w, "Invalid secret or token", http.StatusUnauthorized)
		return
	}

	// Create YAML template
	yamlTemplate := CreateYAMLTemplate(developer)

	w.Header().Set("Content-Type", "text/yaml")
	fmt.Fprintf(w, yamlTemplate)
}

func PostCollectionPointHandler(w http.ResponseWriter, r *http.Request) {
	var data CollectionPointRequest
	err := json.NewDecoder(r.Body).Decode(&data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Verify secret and token
	_, err = VerifyDeveloper(data.Secret, data.Token)
	if err != nil {
		http.Error(w, "Invalid secret or token", http.StatusUnauthorized)
		return
	}

	// Save collection point data
	err = SaveCollectionPointData(data)
	if err != nil {
		http.Error(w, "Failed to save collection point data", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
}

func UpdateCollectionPointHandler(w http.ResponseWriter, r *http.Request) {
	var data CollectionPointUpdateRequest
	err := json.NewDecoder(r.Body).Decode(&data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Verify secret and token
	_, err = VerifyDeveloper(data.Secret, data.Token)
	if err != nil {
		http.Error(w, "Invalid secret or token", http.StatusUnauthorized)
		return
	}

	// Update collection point data
	err = UpdateCollectionPointData(data)
	if err != nil {
		http.Error(w, "Failed to update collection point data", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
}

func GetCollectionPointsHandler(w http.ResponseWriter, r *http.Request) {
	// Implement logic to retrieve collection points
	collectionPoints, err := RetrieveCollectionPoints()
	if err != nil {
		http.Error(w, "Failed to retrieve collection points", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(collectionPoints)
}

// Implement other handlers (PostCollectionPointHandler, UpdateCollectionPointHandler, GetCollectionPointsHandler) similarly
