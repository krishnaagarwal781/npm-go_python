package handlers

import (
	"context"
	"encoding/json"
	"go-python/database"
	"go-python/models"
	"go-python/utils"
	"net/http"
	"time"

	"github.com/go-chi/render"
	"github.com/rs/zerolog/log"
	// "github.com/rs/zerolog/log"
	"go.mongodb.org/mongo-driver/bson"
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

func (h *Handler) PackageRegister(w http.ResponseWriter, r *http.Request) {
	var data models.DeveloperDetails
	if err := json.NewDecoder(r.Body).Decode(&data); err != nil {
		render.Status(r, http.StatusBadRequest)
		render.PlainText(w, r, "Invalid request payload")
		return
	}

	// Generate secret and token
	secret := utils.GenerateUUID()
	token := utils.GenerateUUID()
	

	// Prepare data to insert into MongoDB
	developerData := bson.M{
		"developer_email":   data.DeveloperEmail,
		"developer_website": data.DeveloperWebsite,
		"developer_city":    data.DeveloperCity,
		"developer_mobile":  data.DeveloperMobile,
		"organisation_name": data.OrganisationName,
		"secret":            secret,
		"token":             token,
		"registered_at":     time.Now(),
	}

	insertResult,err:=database.InsertData(context.Background(), h.client, h.cfg.Dbname,"developer_details", developerData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert developer details into mongodb.")
	}

	// Insert data into organisation collection
	orgData := bson.M{
		"organisation_name":    data.OrganisationName,
		"developer_email":      data.DeveloperEmail,
		"developer_details_id": insertResult.InsertedID,
		"registered_at":        time.Now(),
	}

	database.InsertData(context.Background(), h.client, h.cfg.Dbname,"organisation_details", orgData)
	

	response := map[string]string{
		"secret": secret,
		"token":  token,
	}
	render.JSON(w, r, response)
}




func (h *Handler) CreateCollectionPoint(w http.ResponseWriter, r *http.Request) {

// @TODO: Implement this method
}

func (h *Handler) PostCollectionPoint(w http.ResponseWriter, r *http.Request) {

	//@TODO: Implement this method
}

func (h *Handler) UpdateCollectionPoint(w http.ResponseWriter, r *http.Request) {

	// @TODO: Implement this method
}

func (h *Handler) GetCollectionPoints(w http.ResponseWriter, r *http.Request) {
	// @TODO: Implement this method
}