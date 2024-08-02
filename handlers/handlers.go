package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"go-python/database"
	"go-python/models"
	"go-python/utils"
	"net/http"

	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/render"
	"github.com/rs/zerolog/log"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"gopkg.in/yaml.v2"
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


// Home handles the home route.
func (h *Handler) Home(w http.ResponseWriter, r *http.Request) {
	render.PlainText(w, r, "Welcome to Concur API")
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
	secret := utils.GenerateUUID(32)
	token := utils.GenerateUUID(16)

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
	// orgID := r.URL.Query().Get("org_id")
	// orgKey := r.URL.Query().Get("org_key")
	// orgSecret := r.URL.Query().Get("org_secret")

	// Extract params from header
	orgID := r.Header.Get("org_id")
	orgKey := r.Header.Get("org_key")
	orgSecret := r.Header.Get("org_secret")

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

	// Make sure that the app_type is web app mobile app, ctv, pos or other
	// make array of valid app types
	validAppTypes := []string{"web app", "mobile app", "ctv", "pos", "other"}
	// check if the app type is valid
	isValidAppType := false
	for _, validAppType := range validAppTypes {
		if data.AppType == validAppType {
			isValidAppType = true
			break
		}
	}
	if !isValidAppType {
		log.Error().Msg("Invalid app type")
		render.Status(r, http.StatusBadRequest)
		render.JSON(w, r, map[string]string{"message": "Invalid app type. App type must be web app, mobile app, ctv, pos or other"})	
		return
	}

	// Make sure that the app_stage is development, testing, production
	// make array of valid app stages
	validAppStages := []string{"development", "testing", "production"}
	// check if the app stage is valid
	isValidAppStage := false
	for _, validAppStage := range validAppStages {
		if data.AppStage == validAppStage {
			isValidAppStage = true
			break
		}
	}
	if !isValidAppStage {
		log.Error().Msg("Invalid app stage")
		render.Status(r, http.StatusBadRequest)
		render.JSON(w, r, map[string]string{"message": "Invalid app stage. App stage must be development, testing or production"})
		return
	}

	// Check if the application user is one of the following: global, india, eu, usa, saudi arabia
	// make array of valid application users
	validApplicationUsers := []string{"global", "india", "eu", "usa", "saudi arabia"}
	// check if the application user is valid
	isValidApplicationUser := false
	for _, validApplicationUser := range validApplicationUsers {
		if data.ApplicationUser == validApplicationUser {
			isValidApplicationUser = true
			break
		}
	}
	if !isValidApplicationUser {
		log.Error().Msg("Invalid application user")
		render.Status(r, http.StatusBadRequest)
		render.JSON(w, r, map[string]string{"message": "Invalid application user. Application user must be global, india, eu, usa or saudi arabia"})
		return
	}

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

	// loop through the data elements and loop through purposes and add purpose id
	for i, dataElement := range data.DataElements {
		for j, _ := range dataElement.Purposes {
			purposeID := utils.GenerateUUID(8)
			data.DataElements[i].Purposes[j].PurposeID = purposeID
		}
	}

	// Generate default values for the collection point
	collectionPointData := models.CollectionPointData{
		CPName:    data.CollectionPointName,
		CPStatus:  "active",
		CPURL:     "http://default-url.com",
		DataElements: data.DataElements,
		
	}

	
	

	// Prepare the data to insert into MongoDB
	collectionPointDatas := bson.M{
		"org_id":       data.OrgID,
		"app_id":       data.AppID,
		"cp_name":      collectionPointData.CPName,
		"cp_status":    collectionPointData.CPStatus,
		"cp_url":       collectionPointData.CPURL,
		"data_elements": collectionPointData.DataElements,
	}

	



	// Insert data into collection_points
	cpResult, err := database.InsertData(context.Background(), h.client, h.cfg.Dbname, "collection_points", collectionPointDatas)
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

	// orgID := r.URL.Query().Get("org_id")
	// orgKey := r.URL.Query().Get("org_key")
	// orgSecret := r.URL.Query().Get("org_secret")

	// Get params from header
	orgID := r.Header.Get("org_id")
	orgKey := r.Header.Get("org_key")
	orgSecret := r.Header.Get("org_secret")

	log.Debug().Msgf("Deleting collection point: %s", collectionPointID)
	log.Debug().Msgf("Org ID: %s, Org Key: %s, Org Secret: %s", orgID, orgKey, orgSecret)

	// Verify org_key and org_secret
	filter := bson.M{
		"organisation_id": orgID,
		"org_key":         orgKey,
		"org_secret":      orgSecret,
	}

	log.Debug().Msgf("Org ID: %s, Org Key: %s, Org Secret: %s", orgID, orgKey, orgSecret)

	isAuthorised,err:=database.IsAuthorised(context.Background(), h.client, h.cfg.Dbname, "developer_details", filter)
	if err != nil || !isAuthorised {
		log.Error().Err(err).Msg("Failed to verify organisation")
		render.Status(r, http.StatusUnauthorized)
		render.JSON(w, r, map[string]string{"message": "Failed to verify organisation"})
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
		render.JSON(w, r, map[string]string{"message": "Failed to delete collection point"})
		return
	}
	if deleteResult.DeletedCount == 0 {
		render.Status(r, http.StatusNotFound)
		render.JSON(w, r, map[string]string{"message": "Collection point not found"})
		return
	}

	render.JSON(w, r, map[string]string{"message": "Collection point deleted successfully"})

}



// GetCollectionPoints retrieves all collection points for the specified org_id and application_id
func (h *Handler) GetCollectionPoints(w http.ResponseWriter, r *http.Request) {
	// Get query parameters
	// orgID := r.URL.Query().Get("org_id")
	// orgKey := r.URL.Query().Get("org_key")
	// orgSecret := r.URL.Query().Get("org_secret")
	applicationID := chi.URLParam(r, "app_id")

	// Get params from header
	orgID := r.Header.Get("org_id")
	orgKey := r.Header.Get("org_key")
	orgSecret := r.Header.Get("org_secret")

	// Verify org_key and org_secret
	filter := bson.M{
		"organisation_id": orgID,
		"org_key":         orgKey,
		"org_secret":      orgSecret,
	}

	log.Debug().Msgf("Org ID: %s, Org Key: %s, Org Secret: %s", orgID, orgKey, orgSecret)

	isAuthorised,err:=database.IsAuthorised(context.Background(), h.client, h.cfg.Dbname, "developer_details", filter)
	if err != nil || !isAuthorised {
		log.Error().Err(err).Msg("Failed to verify organisation")
		render.Status(r, http.StatusUnauthorized)
		render.JSON(w, r, map[string]string{"message": "Failed to verify organisation"})
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
		render.JSON(w, r, map[string]string{"message": "No collection points found"})
		return
	}

	response := models.GetCollectionPointsResponse{
		CollectionPoints: collectionPoints,
	}

	// set the response content type
	w.Header().Set("Content-Type", "application/json")
	render.JSON(w, r, response)
}


func (h *Handler)GetNoticeInfo(w http.ResponseWriter, r *http.Request){
	// Get app_id, org_id, org_key, org_secret from the headers
	appID := r.Header.Get("app_id")
	orgID := r.Header.Get("org_id")
	orgKey := r.Header.Get("org_key")
	orgSecret := r.Header.Get("org_secret")

	// Get cp_id from the URL path parameters
	collectionPointID := chi.URLParam(r, "cp_id")


	// Verify org_key and org_secret
	filter := bson.M{
		"organisation_id": orgID,
		"org_key":         orgKey,
		"org_secret":      orgSecret,
	}

	log.Debug().Msgf("Org ID: %s, Org Key: %s, Org Secret: %s, App id; %s, CP id : %s", orgID, orgKey, orgSecret,appID, collectionPointID)

	isAuthorised,err:=database.IsAuthorised(context.Background(), h.client, h.cfg.Dbname, "developer_details", filter)
	if err != nil || !isAuthorised {
		log.Error().Err(err).Msg("Failed to verify organisation")
		render.Status(r, http.StatusUnauthorized)
		render.JSON(w, r, map[string]string{"message": "Failed to verify organisation"})
		return
	}

	// Get the collection point details
	collectionPointIDHex, err := primitive.ObjectIDFromHex(collectionPointID)
	if err != nil {
		log.Error().Err(err).Msg("Invalid collection point ID")
		http.Error(w, "Invalid collection point ID", http.StatusBadRequest)
		return
	}

	filter = bson.M{"_id": collectionPointIDHex, "org_id": orgID, "app_id": appID}

	var collectionPointData models.CollectionPointData
	err = database.FindOne(context.Background(), h.client, h.cfg.Dbname, "collection_points", filter).Decode(&collectionPointData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to find collection point")
		http.Error(w, "Collection point not found", http.StatusNotFound)
		return
	}

	noticeInfo := map[string]interface{}{
		"urls": map[string]string{
			"logo":               "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTI2K4cwj_yTWk-rSebFdFF-tX1yMKE8o_Uwnk5H9GYkIoqSKHAvt-pYaB1dEQHK1paNNk&usqp=CAU",
			"speakIcon":          "https://www.svgrepo.com/show/165176/speaking.svg",
			"pauseIcon":          "https://www.svgrepo.com/show/149256/pause-button.svg",
			"arrowIcon":          "https://cdn.icon-icons.com/icons2/2248/PNG/512/arrow_top_right_icon_135926.png",
			"mp3Link":            "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
			"dpar_link":          "https://www.instagram.com",
			"manage_consent_link": "https://www.facebook.com",
		},
	}

	// Populate notice information with details from collectionPointData
	languages := []string{"english", "hindi", "tamil", "telugu", "gujarati", "assamese", "bengali", "bodo", "dogri", "kashmiri"}
	for _, lang := range languages {
		noticeInfo[lang] = map[string]interface{}{
			"collection_point": map[string]interface{}{
				"cp_id":                 collectionPointData.Id,
				"cp_name":               collectionPointData.CPName,
				"cp_status":             collectionPointData.CPStatus,
				"cp_url":                collectionPointData.CPURL,
				"data_elements":         collectionPointData.DataElements, // This should be transformed if needed
			},
			"meta_data": map[string]interface{}{
				"header":                 getHeader(lang),
				"mp3Link":                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
				"title":                  getTitle(lang),
				"description":            getDescription(lang),
				"manage_consent_title":   getManageConsentTitle(lang),
			},
			"button": map[string]string{
				"primary":   getPrimaryButton(lang),
				"secondary": getSecondaryButton(lang),
				"selectAll": getSelectAllButton(lang),
			},
		}
	}

	response := map[string]interface{}{
		"notice_info": noticeInfo,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getHeader(lang string) string {
	headers := map[string]string{
		"english":  "Consent Notice",
		"hindi":    "डेटा सहमति सूचना",
		"tamil":    "ஒப்புதல் அறிவிப்பு",
		"telugu":   "సమ్మతి నోటీసు",
		"gujarati": "મંજુરી સૂચના",
		"assamese": "সম্মতি সূচনা",
		"bengali":  "সম্মতি নোটিশ",
		"bodo":     "अनुमति बिजेनाय",
		"dogri":    "सहमति सूचना",
		"kashmiri": "رضایت نامہ",
	}
	return headers[lang]
}

func getTitle(lang string) string {
	titles := map[string]string{
		"english":  "Digital Personal Data Protection Act 2023",
		"hindi":    "डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023",
		"tamil":    "டிஜிட்டல் தனிப்பட்ட தரவுகளை பாதுகாப்பு சட்டம் 2023",
		"telugu":   "డిజిటల్ వ్యక్తిగత డేటా రక్షణ చట్టం 2023",
		"gujarati": "ડિજિટલ વ્યક્તિગત ડેટા સુરક્ષા અધિનિયમ 2023",
		"assamese": "ডিজিটেল ব্যক্তিগত তথ্য সুৰক্ষা আইন 2023",
		"bengali":  "ডিজিটাল ব্যক্তিগত তথ্য সুরক্ষা আইন 2023",
		"bodo":     "डिजिटल व्यक्तिगत डेटा रक्षा ऐन 2023",
		"dogri":    "डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023",
		"kashmiri": "ڈیجیٹل پرسنل ڈیٹا پروٹیکشن ایکٹ 2023",
	}
	return titles[lang]
}

func getDescription(lang string) string {
	descriptions := map[string]string{
		"english":  "An Act to provide for the processing of digital personal data in a manner that recognises both the right of individuals to protect their personal data and the need to process such personal data for lawful purposes and for matters connected therewith or incidental thereto",
		"hindi":    "डिजिटल व्यक्तिगत डेटा के प्रसंस्करण के लिए इस तरह से प्रावधान करने के लिए एक अधिनियम जो व्यक्तियों के अपने व्यक्तिगत डेटा की सुरक्षा के अधिकार और कानूनी उद्देश्यों के लिए ऐसे व्यक्तिगत डेटा को संसाधित करने की आवश्यकता और उससे जुड़े या उसके प्रासंगिक मामलों को मान्यता देता है।",
		"tamil":    "நபர்களின் தனிப்பட்ட தரவுகளை பாதுகாக்கும் உரிமையை மற்றும் சட்டப்பூர்வமான நோக்கங்களுக்காக அவ்வாறு தனிப்பட்ட தரவுகளை செயலாக்கும் தேவையை கௌரவிக்கும் வகையில் டிஜிட்டல் தனிப்பட்ட தரவுகளை செயலாக்குவதற்கான ஒரு சட்டம் மற்றும் அதனுடன் தொடர்புடைய அல்லது உச்சிகாவியவற்றை சார்ந்த விவகாரங்களுக்கான ஒரு சட்டம்",
		"telugu":   "వ్యక్తుల వ్యక్తిగత డేటా రక్షణ హక్కును మరియు చట్టబద్ధమైన ఉద్దేశ్యాల కోసం ఆ డేటాను ప్రాసెస్ చేయడానికి అవసరాన్ని గుర్తించేవిధంగా డిజిటల్ వ్యక్తిగత డేటా ప్రాసెసింగ్ కోసం ఒక చట్టం మరియు దానికి సంబంధించిన లేదా అనుబంధ విషయాల కోసం",
		"gujarati": "વ્યક્તિઓના વ્યક્તિગત ડેટાને સુરક્ષિત રાખવા હક્ક અને કાનૂની હેતુઓ માટે આવા ડેટાના પ્રોસેસિંગની જરૂરિયાત બંનેને માન્યતા આપતી રીતે ડિજિટલ વ્યક્તિગત ડેટાના પ્રોસેસિંગ માટેનો એક અધિનિયમ અને તેનાથી જોડાયેલા અથવા સબંધિત બાબતો માટે",
		"assamese": "ব্যক্তিৰ ব্যক্তিগত তথ্য সুৰক্ষাৰ অধিকাৰ আৰু আইনানুগ উদ্দেশ্যৰ বাবে সেই ব্যক্তিগত তথ্য প্ৰসেশন কৰিবলৈ প্ৰয়োজনীয়তাক মান্যতা দিয়াৰ কাৰণে ডিজিটেল ব্যক্তিগত তথ্য প্ৰসেশনৰ ব্যৱস্থা কৰিবলৈ এক আইন আৰু তাৰ সৈতে সম্পৰ্কিত বা আনুষঙ্গিক বিষয়ৰ বাবে এক আইন",
		"bengali":  "একটি আইন যা ব্যক্তিরা তাদের ব্যক্তিগত তথ্য সুরক্ষার অধিকার এবং এই ধরনের ব্যক্তিগত তথ্য আইনগত উদ্দেশ্যে প্রক্রিয়া করার প্রয়োজনীয়তা উভয়কেই স্বীকৃতি দেয়, ডিজিটাল ব্যক্তিগত তথ্য প্রক্রিয়া করার জন্য এবং এর সাথে সম্পর্কিত বা আনুষঙ্গিক বিষয়ে একটি আইন",
		"bodo":     "दखालोंगुं आपन व्यक्तिगत डेटा सुरुखो अरथ बिसारवाव अर कानूनी उद्देश्य नाय दादखाल किया होओ बिसारवाव ददरखाय माने ओसोर डाटानाय प्रोससिंग करव फालंगुं बिसार होओ एक ऐन अर हेगोगोनाय संबधि ओसोर या उडातै बिजें नाय एक ऐन",
		"dogri":    "डिजिटल व्यक्तिगत डेटा दे प्रोसेसिंग दे लई इक क़ानून जो की व्यक्तियों दे व्यक्तिगत डेटा दे संरक्षण दे अधिकार अते ऐसे व्यक्तिगत डेटा नू क़ानूनी मकसदां दे लई प्रोसेस करन दी लोड नू मान्यता दिन्दा है, अते उसनाल जुड़े होए या उस दे होर मामले लई",
		"kashmiri": "ایک ایسا قانون جو افراد کے ذاتی ڈیٹا کے تحفظ کے حق اور اس طرح کے ذاتی ڈیٹا کو قانونی مقاصد کے لیے پروسیس کرنے کی ضرورت دونوں کو تسلیم کرتا ہے، ڈیجیٹل ذاتی ڈیٹا پروسیسنگ کے لیے اور اس سے متعلقہ یا اس سے متعلق معاملات کے لیے",
	}
	return descriptions[lang]
}

func getManageConsentTitle(lang string) string {
	manageConsentTitles := map[string]string{
		"english":  "Manage Consent Preferences",
		"hindi":    "सहमति प्राथमिकताएँ प्रबंधित करें",
		"tamil":    "ஒப்புதல் முன்னுரிமைகளை நிர்வகிக்கவும்",
		"telugu":   "సమ్మతి ప్రాధాన్యతలను నిర్వహించండి",
		"gujarati": "મંજુરી પસંદગીઓ મેનેજ કરો",
		"assamese": "সম্মতি পছন্দসমূহ পৰিচালনা কৰক",
		"bengali":  "সম্মতি পছন্দগুলি পরিচালনা করুন",
		"bodo":     "अनुमति प्रायोरिटिज मोजैनाव",
		"dogri":    "सहमति प्राथमिकतावाँ प्रबंधित करो",
		"kashmiri": "رضامندی کی ترجیحات کا نظم کریں",
	}
	return manageConsentTitles[lang]
}

func getPrimaryButton(lang string) string {
	primaryButtons := map[string]string{
		"english":  "Accept",
		"hindi":    "स्वीकार",
		"tamil":    "ஏற்றுக்கொள்",
		"telugu":   "అంగీకరించు",
		"gujarati": "સ્વીકારો",
		"assamese": "গ্ৰহণ কৰক",
		"bengali":  "গ্রহণ করুন",
		"bodo":     "आसरा",
		"dogri":    "स्वीकारो",
		"kashmiri": "قبول کریں",
	}
	return primaryButtons[lang]
}

func getSecondaryButton(lang string) string {
	secondaryButtons := map[string]string{
		"english":  "Cancel",
		"hindi":    "रद्द",
		"tamil":    "ரத்து",
		"telugu":   "రద్దు చేయి",
		"gujarati": "રદ કરો",
		"assamese": "বাতিল কৰক",
		"bengali":  "বাতিল করুন",
		"bodo":     "खतमाव",
		"dogri":    "रद्द करो",
		"kashmiri": "منسوخ کریں",
	}
	return secondaryButtons[lang]
}

func getSelectAllButton(lang string) string {
	selectAllButtons := map[string]string{
		"english":  "Select All",
		"hindi":    "सबका चयन करें",
		"tamil":    "அனைத்தையும் தேர்வுசெய்க",
		"telugu":   "అన్నీ ఎంచుకో",
		"gujarati": "બધા પસંદ કરો",
		"assamese": "সকলো বাছক",
		"bengali":  "সবগুলি নির্বাচন করুন",
		"bodo":     "सब ओनाय चुनाव",
		"dogri":    "सारे चूनो",
		"kashmiri": "سبھی کا انتخاب کریں",
	}
	return selectAllButtons[lang]
}


func (h *Handler) PostConsentPreference(w http.ResponseWriter, r *http.Request){
	var data models.ConsentPreferenceRequest
    if err := json.NewDecoder(r.Body).Decode(&data); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Validate organisation
    organisationFilter := bson.M{
        "organisation_id": data.OrgID,
        "org_key":         data.OrgKey,
        "org_secret":      data.OrgSecret,
    }

    // Verify org_key and org_secret
	isAuthorised,err:=database.IsAuthorised(context.Background(), h.client, h.cfg.Dbname, "developer_details", organisationFilter)
	if err != nil || !isAuthorised {
		log.Error().Err(err).Msg("Failed to verify organisation")
		render.Status(r, http.StatusUnauthorized)
		render.JSON(w, r, map[string]string{"message": "Failed to verify organisation"})
		return
	}

    // Validate collection point and fetch data elements
    cpID, err := primitive.ObjectIDFromHex(data.CPID)
    if err != nil {
        http.Error(w, "Invalid collection point ID format", http.StatusBadRequest)
        return
    }

    collectionPointFilter := bson.M{
        "_id":    cpID,
        "org_id": data.OrgID,
    }

    var collectionPoint bson.M
    err = database.FindOne(context.Background(), h.client,h.cfg.Dbname,"collection_points",collectionPointFilter).Decode(&collectionPoint)
    if err != nil {
        http.Error(w, "Collection point not found", http.StatusNotFound)
        return
    }

    cpName, _ := collectionPoint["cp_name"].(string)
    // dataElements, _ := collectionPoint["data_elements"].([]interface{})

    // Validate that each data_element_name in consent_scope exists in data_elements
    // for _, scopeItem := range data.ConsentScope {
    //     found := false
    //     for _, element := range dataElements {
    //         elemMap := element.(map[string]interface{})
    //         if elemMap["data_element"] == scopeItem.DataElementName {
    //             found = true
    //             break
    //         }
    //     }
    //     if !found {
    //         http.Error(w, "Invalid data_element_name: "+scopeItem.DataElementName, http.StatusBadRequest)
    //         return
    //     }
    // }

    // Build consent document
    consentDocument := bson.M{
        "context":                "https://consent.foundation/artifact/v1",
        "type":                   cpName,
        "agreement_hash_id":      "",
        "agreement_version":      "",
        "linked_agreement_hash":  "",
        "data_principal": bson.M{
            "dp_df_id":        "",
            "dp_public_key":   "",
            "dp_residency":    "",
            "dp_email":        "NULL [Encrypted]",
            "dp_verification": "",
            "dp_child":        "",
            "dp_attorney": bson.M{
                "dp_df_id":      "",
                "dp_public_key": "",
                "dp_email":      "NULL [Encrypted]",
            },
        },
        "data_fiduciary": bson.M{
            "df_id":           "",
            "agreement_date":  "",
            "date_of_consent": time.Now().UTC().Format(time.RFC3339),
            "consent_status":  "active",
            "revocation_date": nil,
        },
        "data_principal_rights": bson.M{
            "right_to_access":            true,
            "right_to_rectify":           true,
            "right_to_erase":             true,
            "right_to_restrict_processing": true,
            "right_to_data_portability":  true,
        },
        "consent_scope":   make([]interface{}, len(data.ConsentScope)),
        "dp_id":           data.DPID,
        "cp_id":           data.CPID,
    }

    for i, scopeItem := range data.ConsentScope {
        consentDocument["consent_scope"].([]interface{})[i] = bson.M{
            "data_element_name": scopeItem.DataElementName,
            "purpose_id":        scopeItem.PurposeID,
            "consent_status":    scopeItem.ConsentStatus,
            "shared":            scopeItem.Shared,
            "data_processor_id": scopeItem.DataProcessorID,
            "cross_border":      scopeItem.CrossBorder,
            "consent_timestamp": time.Now().UTC().Format(time.RFC3339),
            "expiry_date":       time.Now().UTC().Format(time.RFC3339),
        }
    }



    filter := bson.M{"dp_id": data.DPID, "cp_id": data.CPID}
    update := bson.M{"$set": consentDocument}

	agreementID, created, err := database.UpsertDocument(context.Background(), h.client, h.cfg.Dbname, "consent_preferences", filter, update)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

	responseMessage := "Consent preferences updated successfully"
    if created {
        responseMessage = "Consent preferences created successfully"
    }

    json.NewEncoder(w).Encode(models.PostConsentPreferenceResponse{
        Message:    responseMessage,
        AgreementID: agreementID.Hex(),
    })
}