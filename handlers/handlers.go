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
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/render"
	"github.com/rs/zerolog/log"
	"gopkg.in/yaml.v2"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
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


// PackageRegister handles the registration of a new package.
func (h *Handler) PackageRegister(w http.ResponseWriter, r *http.Request) {
	var data models.DeveloperDetails
	// Decode the request payload
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
		"org_key":             token,
		"registered_at":     time.Now(),
		"client_ip":         clientIP,
		"headers":           headers,
	}

	// Insert data into developer collection
	insertDevResult,err:=database.InsertData(context.Background(), h.client, h.cfg.Dbname,"developer_details", developerData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert developer details into mongodb.")
		render.Status(r, http.StatusInternalServerError)
		render.JSON(w, r, map[string]string{"message": "Failed to insert developer details into mongodb."})
		return
	}




	// Prepare data to insert into organisation collection
	orgData := bson.M{
		"organisation_name":    data.OrganisationName,
		"developer_email":      data.DeveloperEmail,
		"developer_details_id": utils.ConvertObjectIDToString(insertDevResult.InsertedID),
		"registered_at":        time.Now(),
	}

	// Insert data into organisation collection
	insertOrgResult,err:=database.InsertData(context.Background(), h.client, h.cfg.Dbname,"organisation_details", orgData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert organisation details into mongodb.")
		render.Status(r, http.StatusInternalServerError)
		render.JSON(w, r, map[string]string{"message": "Failed to insert organisation details into mongodb."})
		return
	}

	// update the developer details with the organisation id
	update := bson.M{
		"$set": bson.M{
			"organisation_id": utils.ConvertObjectIDToString(insertOrgResult.InsertedID),
		},
	}
	filter := bson.M{"_id": insertDevResult.InsertedID}
	_,err = database.UpdateData(context.Background(), h.client, h.cfg.Dbname,"developer_details", filter, update)
	if err != nil {
		log.Error().Err(err).Msg("Failed to update developer details")
		render.Status(r, http.StatusInternalServerError)
		render.JSON(w, r, map[string]string{"message": "Failed to update developer details"})
		return
	}



	// Prepare the response
	response := map[string]string{
		"con_org_id":   utils.ConvertObjectIDToString(insertOrgResult.InsertedID),
		"con_org_key":  token,
		"con_org_secret": secret,
	}
	render.JSON(w, r, response)
}


// CreateApplication handles the creation of a new application.
func (h *Handler) CreateApplication(w http.ResponseWriter, r *http.Request) {
	var data models.ApplicationDetails
	// Decode the request payload
	if err := json.NewDecoder(r.Body).Decode(&data); err != nil {
		render.Status(r, http.StatusBadRequest)
		render.PlainText(w, r, "Invalid request payload")
		return
	}

	// Extract parameters from URL queries
	orgID := r.URL.Query().Get("org_id")
	orgKey := r.URL.Query().Get("org_key")
	orgSecret := r.URL.Query().Get("org_secret")

	log.Debug().Msgf("Org ID: %s, Org Key: %s, Org Secret: %s", orgID, orgKey, orgSecret)


	// verify the organisation id, key and secret
	filter:=bson.M{"organisation_id": orgID, "org_key": orgKey, "org_secret": orgSecret}
	isAuthorised,err:=database.IsAuthorised(context.Background(), h.client, h.cfg.Dbname,"developer_details", filter)
	if err != nil || !isAuthorised {
		log.Error().Err(err).Msg("Failed to verify organisation")
		render.Status(r, http.StatusUnauthorized)
		render.JSON(w, r, map[string]string{"message": "Failed to verify organisation"})
		return
	}


	log.Debug().Msgf("Creating application for org_id: %s", orgID)


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

	// Insert data into org_applications
	_,err = database.InsertData(context.Background(), h.client, h.cfg.Dbname,"org_applications", appData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert application details into mongodb.")
		render.Status(r, http.StatusInternalServerError)
		render.JSON(w, r, map[string]string{"message": "Failed to insert application details into mongodb."})
		return
	}

	
	// Generate YAML template
	yamlTemplate := models.YamlTemplate{
		Version: "1.0",
		OrganisationID: orgID,
		Applications: []models.Application{
			{
				ApplicationID:    appID,
				Type:             data.AppType,
				Name: 		   	  data.AppName,
				Stage: 		  	  data.AppStage,
				ApplicationUser: data.ApplicationUser,
				CollectionPoints: []models.CollectionPointData{},
			},
		},
	}

	

	

	// Prepare the response
	response := models.ApplicationResponse{
		YamlData: yamlTemplate,
		Con_app_id: appID,
		App_type: data.AppType,
		App_name: data.AppName,
		App_stage: data.AppStage,
		Application_user: data.ApplicationUser,
	}

	// Marshal the response
	jsonResponse, err := json.Marshal(response)
	if err != nil {
		log.Error().Err(err).Msg("Failed to marshal response")
		render.Status(r, http.StatusInternalServerError)
		render.JSON(w, r, map[string]string{"message": "Failed to marshal response"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(jsonResponse)
}






// CreateCollectionPoint handles the creation of a new collection point.
func (h *Handler) CreateCollectionPoint(w http.ResponseWriter, r *http.Request) {

	var data models.CollectionPointRequest

	// Decode the request payload
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

	log.Debug().Msgf("Org ID: %s, Org Key: %s, Org Secret: %s", data.OrgID, data.OrganisationKey, data.OrganisationSecret)

	isAuthorised, err:=database.IsAuthorised(context.Background(), h.client, h.cfg.Dbname, "developer_details", filter)
	if err != nil || !isAuthorised {
		log.Error().Err(err).Msg("Failed to verify organisation")
		render.Status(r, http.StatusUnauthorized)
		render.JSON(w, r, map[string]string{"message": "Failed to verify organisation"})
		return
	}

	// Generate default values for the collection point
	collectionPointData := models.CollectionPointData{
		CPName:    data.CollectionPointName,
		CPStatus:  "active",
		CPURL:     "http://default-url.com",
		DataElements: data.DataElements,
		
	}

	// Insert data into collection_points
	cpResult, err := database.InsertData(context.Background(), h.client, h.cfg.Dbname, "collection_points", collectionPointData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert collection point details into mongodb.")
		render.Status(r, http.StatusInternalServerError)
		render.JSON(w, r, map[string]string{"message": "Failed to insert collection point details into mongodb."})
		return
	}

	// Convert the cpID to a string
	cpID := utils.ConvertObjectIDToString(cpResult.InsertedID)
	collectionPointData.Id = cpID
	
	message := fmt.Sprintf("Collection point with %s created successfully", cpID)

	response := models.CollectionPointResponse{
		Message: message,
		CollectionPointData: collectionPointData,
	}

	// Marshal the response
	jsonResponse, err := json.Marshal(response)
	if err != nil {
		log.Error().Err(err).Msg("Failed to marshal response")
		render.Status(r, http.StatusInternalServerError)
		render.JSON(w, r, map[string]string{"message": "Failed to marshal response"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(jsonResponse)

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

	// Verify org_key and org_secret
	isAuthorised,err:=database.IsAuthorised(context.Background(), h.client, h.cfg.Dbname, "developer_details", filter)
	if err != nil || !isAuthorised {
		log.Error().Err(err).Msg("Failed to verify organisation")
		render.Status(r, http.StatusUnauthorized)
		render.JSON(w, r, map[string]string{"message": "Failed to verify organisation"})
		return
	}

	// Get the uploaded YAML file
	file, _, err := r.FormFile("yaml_file")
	if err != nil {
		log.Error().Err(err).Msg("Failed to get YAML file")
		render.Status(r, http.StatusBadRequest)
		render.JSON(w, r, map[string]string{"message": "Failed to get YAML file"})
		return
	}
	defer file.Close()

	// Read the YAML file
	var yamlData models.YamlTemplate
	decoder := yaml.NewDecoder(file)
	if err := decoder.Decode(&yamlData); err != nil {
		log.Error().Err(err).Msg("Failed to decode YAML file")
		render.Status(r, http.StatusBadRequest)
		render.JSON(w, r, map[string]string{"message": "Failed to decode YAML file"})
		return
	}

	if yamlData.OrganisationID != orgID {
		log.Error().Msg("Organisation ID mismatch")
		render.Status(r, http.StatusBadRequest)
		render.JSON(w, r, map[string]string{"message": "Organisation ID mismatch"})
		return
	}

	// Iterate through the applications field in the YAML data
	for _, application := range yamlData.Applications {
		if application.ApplicationID == appID {

			// Iterate through the collection points of the application
			for _, cp := range application.CollectionPoints {
				// Convert the cpID to ObjectID
				cpID, err := primitive.ObjectIDFromHex(cp.Id)
				if err != nil {
					log.Error().Err(err).Msg("Invalid collection point ID")
					render.Status(r, http.StatusBadRequest)
					render.JSON(w, r, map[string]string{"message": "Invalid collection point ID"})
					return
				}
				filter := bson.M{"_id": cpID}
	
				// Check the count of documents with the filter
				count, err := database.CountDocuments(context.Background(), h.client, h.cfg.Dbname, "collection_points", filter)
				if err != nil {
					log.Error().Err(err).Msg("Failed to count collection points")
					render.Status(r, http.StatusInternalServerError)
					render.PlainText(w, r, "Failed to count collection points")
					return
				}
				log.Debug().Msgf("CP ID %s, Count %d", cpID.Hex(), count)
				// Insert or update the collection point
				if count == 0 {
					// // Insert new collection point
					// cpData := bson.M{
					// 	"_id":          cpID,
					// 	"org_id":       orgID,
					// 	"app_id":       appID,
					// 	"cp_name":      cp.CPName,
					// 	"cp_status":    cp.CPStatus,
					// 	"cp_url":       cp.CPURL,
					// 	"data_elements": cp.DataElements,
					// }
					// _, err := database.InsertData(context.Background(), h.client, h.cfg.Dbname, "collection_points", cpData)
					// if err != nil {
					// 	log.Error().Err(err).Msg("Failed to insert collection point")
					// 	render.Status(r, http.StatusInternalServerError)
					// 	render.PlainText(w, r, "Failed to insert collection point")
					// 	return
					// }

					// Collection point not found
					log.Debug().Msg("Collection point not found")
					render.Status(r, http.StatusNotFound)
					render.JSON(w, r, map[string]string{"message": "Collection point "+cp.Id+" not found. Please create it first."})
					return

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
					_, err = database.UpdateData(context.Background(), h.client, h.cfg.Dbname, "collection_points", filter, update)
					if err != nil {
						log.Error().Err(err).Msg("Failed to update collection point")
						render.Status(r, http.StatusInternalServerError)
						render.JSON(w, r, map[string]string{"message": "Failed to update collection point"})
						return
					}
				}
			}
		}
	}
	
	response := models.YamlUpdateResponse{
		Message: "YAML file updated successfully",
		YamlData: yamlData,
	}

	// Marshal the response
	jsonResponse, err := json.Marshal(response)
	if err != nil {
		log.Error().Err(err).Msg("Failed to marshal response")
		render.Status(r, http.StatusInternalServerError)
		render.JSON(w, r, map[string]string{"message": "Failed to marshal response"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(jsonResponse)
}



// DeleteCollectionPoint handles the deletion of a collection point and updates MongoDB and YAML file accordingly
func (h *Handler) DeleteCollectionPoint(w http.ResponseWriter, r *http.Request) {
	// Get the collection point ID from the URL parameters
	collectionPointID := chi.URLParam(r, "collection_point_id")

	orgID := r.URL.Query().Get("org_id")
	orgKey := r.URL.Query().Get("org_key")
	orgSecret := r.URL.Query().Get("org_secret")

	log.Debug().Msgf("Deleting collection point: %s", collectionPointID)
	log.Debug().Msgf("Org ID: %s, Org Key: %s, Org Secret: %s", orgID, orgKey, orgSecret)

	// Verify org_key and org_secret
	filter := bson.M{
		"organisation_id": orgID,
		"org_key":         orgKey,
		"org_secret":      orgSecret,
	}

	log.Debug().Msgf("Org ID: %s, Org Key: %s, Org Secret: %s", orgID, orgKey, orgSecret)

	count,err := database.CountDocuments(context.Background(), h.client, h.cfg.Dbname,"developer_details", filter)
	if err != nil {
		log.Error().Err(err).Msg("Failed to find organisation")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to verify organisation")
		return
	}
	if count == 0 {
		log.Debug().Msg("Invalid org_key or org_secret")
		render.Status(r, http.StatusUnauthorized)
		render.PlainText(w, r, "Invalid org_key or org_secret")
		return
	}

	// convert collectionPointID to primitive.ObjectID
	collectionPointIDHex, err := primitive.ObjectIDFromHex(collectionPointID)
	if err != nil {
		log.Error().Err(err).Msg("Invalid collection point ID")
		render.Status(r, http.StatusBadRequest)
		render.PlainText(w, r, "Invalid collection point ID")
		return
	}

	// Delete collection point from MongoDB
	filter = bson.M{"_id": collectionPointIDHex, "org_id": orgID}
	deleteResult, err := database.DeleteOne(context.Background(), h.client, h.cfg.Dbname, "collection_points", filter)
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

	// Read the YAML file
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
		// Iterate backward through the collection points of each application
		for j := len(yamlData.Applications[i].CollectionPoints) - 1; j >= 0; j-- {
			if yamlData.Applications[i].CollectionPoints[j].Id == collectionPointID {
				// Delete collection point
				yamlData.Applications[i].CollectionPoints = append(
					yamlData.Applications[i].CollectionPoints[:j],
					yamlData.Applications[i].CollectionPoints[j+1:]...,
				)
			}
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

	log.Debug().Msgf("Org ID: %s, Org Key: %s, Org Secret: %s", orgID, orgKey, orgSecret)

	count,err := database.CountDocuments(context.Background(), h.client, h.cfg.Dbname,"developer_details", filter)
	if err != nil {
		log.Error().Err(err).Msg("Failed to find organisation")
		render.Status(r, http.StatusInternalServerError)
		render.PlainText(w, r, "Failed to verify organisation")
		return
	}
	if count == 0 {
		log.Debug().Msg("Invalid org_key or org_secret")
		render.Status(r, http.StatusUnauthorized)
		render.PlainText(w, r, "Invalid org_key or org_secret")
		return
	}


	// Retrieve all collection points for the specified org_id and application_id
	filter = bson.M{"org_id": orgID, "app_id": applicationID}
	cursor, err := database.FindData(context.Background(), h.client, h.cfg.Dbname, "collection_points", filter)
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
