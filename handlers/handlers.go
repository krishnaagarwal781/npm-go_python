package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"go-python/database"
	"go-python/models"
	"go-python/utils"
	"net/http"
	"os"
	// "strconv"

	// "strconv"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/render"
	"github.com/rs/zerolog/log"
	"gopkg.in/yaml.v2"

	// "github.com/rs/zerolog/log"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

// Handler represents the application handler.
type Handler struct {
	client *mongo.Client
	cfg    *models.Config
}

// NewHandler creates a new handler.
func NewHandler(client *mongo.Client, cfg *models.Config) *Handler {
	return &Handler{
		client: client,
		cfg:    cfg,
	}
}

func (h *Handler) PackageRegister(w http.ResponseWriter, r *http.Request) {
	var data models.DeveloperDetails
	if err := json.NewDecoder(r.Body).Decode(&data); err != nil {
		render.Status(r, http.StatusBadRequest)
		render.PlainText(w, r, "Invalid request payload")
		return
	}

	// Generate secret and token
	secret := utils.GenerateUUID(16)
	token := utils.GenerateUUID(32)

	// Extract client IP and headers
	clientIP := utils.GetClientIP(r)
	headers := utils.GetHeaders(r)
	

	// Prepare data to insert into MongoDB
	developerData := bson.M{
		"developer_email":   data.DeveloperEmail,
		"developer_website": data.DeveloperWebsite,
		"developer_city":    data.DeveloperCity,
		"developer_mobile":  data.DeveloperMobile,
		"organisation_name": data.OrganisationName,
		"org_secret":            secret,
		"org_token":             token,
		"registered_at":     time.Now(),
		"client_ip":         clientIP,
		"headers":           headers,
	}

	insertDevResult,err:=database.InsertData(context.Background(), h.client, h.cfg.Dbname,"developer_details", developerData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert developer details into mongodb.")
	}

	// Insert data into organisation collection
	orgData := bson.M{
		"organisation_name":    data.OrganisationName,
		"developer_email":      data.DeveloperEmail,
		"developer_details_id": insertDevResult.InsertedID,
		"registered_at":        time.Now(),
	}

	insertOrgResult,err:=database.InsertData(context.Background(), h.client, h.cfg.Dbname,"organisation_details", orgData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert organisation details into mongodb.")
	}

	// update the developer details with the organisation id
	update := bson.M{
		"$set": bson.M{
			"organisation_id": insertOrgResult.InsertedID,
		},
	}
	filter := bson.M{"_id": insertDevResult.InsertedID}
	_,err = database.UpdateData(context.Background(), h.client, h.cfg.Dbname,"developer_details", filter, update)
	if err != nil {
		log.Error().Err(err).Msg("Failed to update developer details")
	}

	envContent := fmt.Sprintf("ORG_ID=%s\nORG_KEY=%s\nORG_SECRET=%s\n", insertOrgResult.InsertedID, token, secret)
	err = os.WriteFile(".env", []byte(envContent), 0644)
	if err != nil {
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to write .env file")
		log.Error().Err(err).Msg("Error writing .env file:")
		return
	}
	


	response := map[string]string{
		"secret": secret,
		"token":  token,
	}
	render.JSON(w, r, response)
}



func (h *Handler) CreateApplication(w http.ResponseWriter, r *http.Request) {
	var data models.ApplicationDetails

	if err := json.NewDecoder(r.Body).Decode(&data); err != nil {
		render.Status(r, http.StatusBadRequest)
		render.PlainText(w, r, "Invalid request payload")
		return
	}

	// Extract parameters from URL queries
	orgID := r.URL.Query().Get("org_id")
	orgKey := r.URL.Query().Get("org_key")
	orgSecret := r.URL.Query().Get("org_secret")


	// verify the organisation id, key and secret
	filter:=bson.M{"_id": orgID, "organisation_key": orgKey, "organisation_secret": orgSecret}
	_,err := database.FindData(context.Background(), h.client, h.cfg.Dbname,"organisation_details", filter)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			render.Status(r, http.StatusUnauthorized)
			render.PlainText(w, r, "Invalid org_key or org_secret")
			return
		}
		log.Error().Err(err).Msg("Failed to find organisation")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to verify organisation")
		return
	}


	// Generate application id
	appID := utils.GenerateUUID(8)

	// Prepare the data to insert into MongoDB
	appData := bson.M{
		"org_id":           orgID,
		"app_id":           appID,
		"app_type":         data.AppType,
		"app_name":         data.AppName,
		"app_stage":        data.AppStage,
		"application_user": data.ApplicationUser,
		"registered_at":    time.Now(),
	}

	// @TODO: change the collection name to something more meaningful
	_,err = database.InsertData(context.Background(), h.client, h.cfg.Dbname,"application_collection", appData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert application details into mongodb.")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to insert application details into mongodb.")
		return
	}

	
	// Generate YAML template
	yamlTemplate := models.YamlTemplate{
		Version: "1.0",
		Applications: []models.Application{
			{
				ApplicationID:    appID,
				Type:             data.AppType,
				CollectionPoints: []models.CollectionPointData{},
			},
		},
	}

	yamlData, err := yaml.Marshal(&yamlTemplate)
	if err != nil {
		log.Error().Err(err).Msg("Failed to marshal YAML data")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to generate YAML template")
		return
	}

	// Write the YAML data to a file
	yamlFilename := fmt.Sprintf("%s_applications.yaml", orgID)
	err = os.WriteFile( yamlFilename, yamlData, 0644)
	if err != nil {
		log.Error().Err(err).Msg("Failed to write YAML file")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to write YAML file")
		return
	}


	response := map[string]string{
		"app_id": appID,
		"app_type": data.AppType,
	}

	render.JSON(w, r, response)
}







func (h *Handler) CreateCollectionPoint(w http.ResponseWriter, r *http.Request) {

	var data models.CollectionPointRequest

	if err := json.NewDecoder(r.Body).Decode(&data); err != nil {
		render.Status(r, http.StatusBadRequest)
		render.PlainText(w, r, "Invalid request payload")
		return
	}

	// Verify org_key and org_secret
	filter := bson.M{
		"organisation_id": data.OrgID,
		"org_key":         data.OrganisationKey,
		"org_secret":      data.OrganisationSecret,
	}

	_,err := database.FindData(context.Background(), h.client, h.cfg.Dbname, "organisation_details", filter)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			render.Status(r, http.StatusUnauthorized)
			render.PlainText(w, r, "Invalid org_key or org_secret")
			return
		}
		log.Error().Err(err).Msg("Failed to find organisation")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to verify organisation")
		return
	}

	// Generate default values for the collection point
	collectionPointData := models.CollectionPointData{
		OrgID:     data.OrgID,
		AppID:     data.AppID,
		CPName:    "Default Collection Point",
		CPStatus:  "active",
		CPURL:     "http://default-url.com",
		DataElements: []models.DataElement{
			{
				DataElement:                 "default_element",
				DataElementTitle:            "Default Element Title",
				DataElementDescription:      "Default Element Description",
				DataOwner:                   "Default Owner",
				LegalBasis:                  "Default Legal Basis",
				RetentionPeriod:             "1 year",
				CrossBorder:                 false,
				Sensitive:                   false,
				Encrypted:                   true,
				Expiry:                      "Never",
				DataElementCollectionStatus: "active",
				Purposes: []models.Purpose{
					{
						PurposeID:          "default_purpose_id",
						PurposeDescription: "Default Purpose Description",
						PurposeLanguage:    "EN",
					},
				},
			},
		},
	}

	// Insert data into collection_point_collection
	cpResult, err := database.InsertData(context.Background(), h.client, h.cfg.Dbname, "collection_point_collection", collectionPointData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert collection point details into mongodb.")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to insert collection point details into mongodb.")
		return
	}

	cpID := cpResult.InsertedID
	

	// Read the existing YAML file
	yamlFilename := fmt.Sprintf("%s_applications.yaml", data.OrgID)
	yamlFile, err := os.ReadFile(yamlFilename)
	if err != nil {
		log.Error().Err(err).Msg("Failed to read YAML file")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to read YAML file")
		return
	}

	var yamlData models.YamlTemplate
	if err := yaml.Unmarshal(yamlFile, &yamlData); err != nil {
		log.Error().Err(err).Msg("Failed to unmarshal YAML file")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to unmarshal YAML file")
		return
	}

	// Convert the cpID to string
	cpIDString := cpID.(primitive.ObjectID).Hex()

	collectionPointData.Id = cpIDString

	// Update the YAML data
	for i := range yamlData.Applications {
		if yamlData.Applications[i].ApplicationID == data.AppID {
			yamlData.Applications[i].CollectionPoints = append(yamlData.Applications[i].CollectionPoints, collectionPointData) 
			break
		}
	}

	// Write the updated YAML data back to the file
	newYamlData, err := yaml.Marshal(&yamlData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to marshal updated YAML data")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to marshal updated YAML data")
		return
	}

	if err := os.WriteFile(yamlFilename, newYamlData, 0644); err != nil {
		log.Error().Err(err).Msg("Failed to write updated YAML file")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to write updated YAML file")
		return
	}

	render.JSON(w, r, map[string]string{"message": "Collection point created successfully"})

}


// PushYaml handles the YAML file upload and updates MongoDB accordingly
func (h *Handler) PushYaml(w http.ResponseWriter, r *http.Request) {
	// Parse the multipart form
	err := r.ParseMultipartForm(10 << 20) // 10 MB
	if err != nil {
		render.Status(r, http.StatusBadRequest)
		render.PlainText(w, r, "Failed to parse form")
		return
	}

	// Get form values
	orgID := r.FormValue("org_id")
	appID := r.FormValue("app_id")
	orgKey := r.FormValue("org_key")
	orgSecret := r.FormValue("org_secret")

	// Verify org_key and org_secret
	filter := bson.M{
		"organisation_id": orgID,
		"org_key":         orgKey,
		"org_secret":      orgSecret,
	}

	_, err = database.FindData(context.Background(), h.client, h.cfg.Dbname, "organisation_details", filter)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			render.Status(r, http.StatusUnauthorized)
			render.PlainText(w, r, "Invalid org_key or org_secret")
			return
		}
		log.Error().Err(err).Msg("Failed to find organisation")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to verify organisation")
		return
	}

	// Get the uploaded YAML file
	file, _, err := r.FormFile("yaml_file")
	if err != nil {
		render.Status(r, http.StatusBadRequest)
		render.PlainText(w, r, "Failed to get the uploaded file")
		return
	}
	defer file.Close()

	// Read the YAML file
	var yamlData models.YamlTemplate
	decoder := yaml.NewDecoder(file)
	if err := decoder.Decode(&yamlData); err != nil {
		render.Status(r, http.StatusBadRequest)
		render.PlainText(w, r, fmt.Sprintf("Invalid YAML file: %v", err))
		return
	}

	// Process each collection point in the YAML data
	for _, application := range yamlData.Applications {
		if application.ApplicationID == appID {
			for _, cp := range application.CollectionPoints {
				cpID := cp.Id
				filter := bson.M{"_id": cpID}
				var existingCP models.CollectionPointData
				err := database.FindOne(context.Background(), h.client, h.cfg.Dbname, "collection_point_collection", filter).Decode(&existingCP)
				if err != nil && err != mongo.ErrNoDocuments {
					log.Error().Err(err).Msg("Failed to find collection point")
					render.Status(r, http.StatusInternalServerError)
					render.PlainText(w, r, "Failed to find collection point")
					return
				}

				if err == mongo.ErrNoDocuments {
					// Insert new collection point
					cpData := models.CollectionPointData{
						OrgID:      orgID,
						AppID:      appID,
						CPName:     cp.CPName,
						CPStatus:   cp.CPStatus,
						CPURL:      cp.CPURL,
						DataElements: cp.DataElements,
					}
					cpResult, err := database.InsertData(context.Background(), h.client, h.cfg.Dbname, "collection_point_collection", cpData)
					if err != nil {
						log.Error().Err(err).Msg("Failed to insert collection point")
						render.Status(r, http.StatusInternalServerError)
						render.PlainText(w, r, "Failed to insert collection point")
						return
					}
					cp.Id = cpResult.InsertedID.(string)
				} else {
					// Update existing collection point
					update := bson.M{
						"$set": bson.M{
							"cp_name":      cp.CPName,
							"cp_status":    cp.CPStatus,
							"cp_url":       cp.CPURL,
							"data_elements": cp.DataElements,
						},
					}
					_, err = database.UpdateData(context.Background(), h.client, h.cfg.Dbname, "collection_point_collection", filter, update)
					if err != nil {
						log.Error().Err(err).Msg("Failed to update collection point")
						render.Status(r, http.StatusInternalServerError)
						render.PlainText(w, r, "Failed to update collection point")
						return
					}
				}
			}
		}
	}

	// Write the updated YAML data back to the file
	yamlFilename := fmt.Sprintf("%s_applications.yaml", orgID)
	newYamlData, err := yaml.Marshal(&yamlData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to marshal updated YAML data")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to marshal updated YAML data")
		return
	}

	if err := os.WriteFile(yamlFilename, newYamlData, 0644); err != nil {
		log.Error().Err(err).Msg("Failed to write updated YAML file")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to write updated YAML file")
		return
	}

	render.JSON(w, r, map[string]string{"message": "YAML file updated successfully"})
}



// DeleteCollectionPoint handles the deletion of a collection point and updates MongoDB and YAML file accordingly
func (h *Handler) DeleteCollectionPoint(w http.ResponseWriter, r *http.Request) {
	collectionPointID := chi.URLParam(r, "collection_point_id")
	orgID := r.URL.Query().Get("org_id")
	orgKey := r.URL.Query().Get("org_key")
	orgSecret := r.URL.Query().Get("org_secret")

	// Verify org_key and org_secret
	filter := bson.M{
		"organisation_id": orgID,
		"org_key":         orgKey,
		"org_secret":      orgSecret,
	}

	var organisation models.OrganisationDetails
	err := database.FindOne(context.Background(), h.client, h.cfg.Dbname, "organisation_details", filter).Decode(&organisation)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			render.Status(r, http.StatusUnauthorized)
			render.PlainText(w, r, "Invalid org_key or org_secret")
			return
		}
		log.Error().Err(err).Msg("Failed to find organisation")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to verify organisation")
		return
	}

	// Delete collection point from MongoDB
	filter = bson.M{"_id": collectionPointID, "org_id": orgID}
	deleteResult, err := database.DeleteOne(context.Background(), h.client, h.cfg.Dbname, "collection_point_collection", filter)
	if err != nil {
		log.Error().Err(err).Msg("Failed to delete collection point")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to delete collection point")
		return
	}
	if deleteResult.DeletedCount == 0 {
		render.Status(r, http.StatusNotFound)
		render.PlainText(w, r, "Collection point not found")
		return
	}

	// Update YAML file to remove the collection point
	yamlFilename := fmt.Sprintf("%s_applications.yaml", orgID)
	yamlFile, err := os.ReadFile(yamlFilename)
	if err != nil {
		log.Error().Err(err).Msg("Failed to read YAML file")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to read YAML file")
		return
	}

	var yamlData models.YamlTemplate
	err = yaml.Unmarshal(yamlFile, &yamlData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to unmarshal YAML file")
		render.Status(r, http.StatusBadRequest)
		render.PlainText(w, r, "Failed to unmarshal YAML file")
		return
	}

	// Remove the collection point from the YAML data
	for i := range yamlData.Applications {
		if yamlData.Applications[i].ApplicationID == collectionPointID {
			var updatedCollectionPoints []models.CollectionPointData
			for _, cp := range yamlData.Applications[i].CollectionPoints {
				if cp.Id != collectionPointID {
					updatedCollectionPoints = append(updatedCollectionPoints, cp)
				}
			}
			yamlData.Applications[i].CollectionPoints = updatedCollectionPoints
			break
		}
	}

	// Write the updated YAML data back to the file
	newYamlData, err := yaml.Marshal(&yamlData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to marshal updated YAML data")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to marshal updated YAML data")
		return
	}

	if err := os.WriteFile(yamlFilename, newYamlData, 0644); err != nil {
		log.Error().Err(err).Msg("Failed to write updated YAML file")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to write updated YAML file")
		return
	}

	render.JSON(w, r, map[string]string{"message": "Collection point deleted successfully"})
}



// GetCollectionPoints retrieves all collection points for the specified org_id and application_id
func (h *Handler) GetCollectionPoints(w http.ResponseWriter, r *http.Request) {
	// Get query parameters
	orgID := r.URL.Query().Get("org_id")
	orgKey := r.URL.Query().Get("org_key")
	orgSecret := r.URL.Query().Get("org_secret")
	applicationID := r.URL.Query().Get("application_id")

	// Verify org_key and org_secret
	filter := bson.M{
		"organisation_id": orgID,
		"org_key":         orgKey,
		"org_secret":      orgSecret,
	}

	var organisation models.OrganisationDetails
	err := database.FindOne(context.Background(), h.client, h.cfg.Dbname, "organisation_details", filter).Decode(&organisation)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			render.Status(r, http.StatusUnauthorized)
			render.PlainText(w, r, "Invalid org_key or org_secret")
			return
		}
		log.Error().Err(err).Msg("Failed to find organisation")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to verify organisation")
		return
	}

	// Retrieve all collection points for the specified org_id and application_id
	filter = bson.M{"org_id": orgID, "app_id": applicationID}
	cursor, err := database.FindData(context.Background(), h.client, h.cfg.Dbname, "collection_point_collection", filter)
	if err != nil {
		log.Error().Err(err).Msg("Failed to find collection points")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to find collection points")
		return
	}
	defer cursor.Close(context.Background())

	var collectionPoints []models.CollectionPointData
	if err = cursor.All(context.Background(), &collectionPoints); err != nil {
		log.Error().Err(err).Msg("Failed to decode collection points")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to decode collection points")
		return
	}

	if len(collectionPoints) == 0 {
		render.Status(r, http.StatusNotFound)
		render.PlainText(w, r, "No collection points found")
		return
	}

	

	render.JSON(w, r, map[string]interface{}{"collection_points": collectionPoints})
}
