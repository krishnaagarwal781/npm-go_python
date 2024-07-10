package main

import (
	"context"
	"encoding/json"
	"log"
	"time"

	"github.com/gofrs/uuid"
	"github.com/valyala/fasthttp"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"gopkg.in/yaml.v2"
)

// DeveloperDetails represents developer registration data.
type DeveloperDetails struct {
	DeveloperEmail   string `json:"developer_email"`
	DeveloperWebsite string `json:"developer_website"`
	DeveloperCity    string `json:"developer_city"`
	DeveloperMobile  string `json:"developer_mobile"`
	OrganisationName string `json:"organisation_name"`
}

// OrganisationDetails represents organisation registration data.
type OrganisationDetails struct {
	OrganisationName string `json:"organisation_name"`
	DeveloperEmail   string `json:"developer_email"`
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

// MongoDB configuration
const (
	MongoDBURI    = "mongodb+srv://sniplyuser:NXy7R7wRskSrk3F2@cataxprod.iwac6oj.mongodb.net/?retryWrites=true&w=majority"
	DatabaseName  = "python-go"
	CollectionDev = "developer_details"
	CollectionOrg = "organisation_details"
	CollectionCP  = "collection_points"
)

var (
	mongoClient *mongo.Client
	ctx         context.Context
)

func init() {
	// Initialize MongoDB client
	var err error
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	mongoClient, err = mongo.Connect(ctx, options.Client().ApplyURI(MongoDBURI))
	if err != nil {
		log.Fatalf("Failed to connect to MongoDB: %v", err)
	}

	// Verify connection
	err = mongoClient.Ping(ctx, nil)
	if err != nil {
		log.Fatalf("Failed to ping MongoDB: %v", err)
	}
}

func main() {
	// Start server
	log.Fatal(fasthttp.ListenAndServe(":8080", requestHandler))
}

func requestHandler(ctx *fasthttp.RequestCtx) {
	switch string(ctx.Path()) {
	case "/package-register":
		if string(ctx.Method()) == fasthttp.MethodPost {
			packageRegister(ctx)
		} else {
			ctx.Error("Method not allowed", fasthttp.StatusMethodNotAllowed)
		}
	case "/create-collection-point":
		if string(ctx.Method()) == fasthttp.MethodPost {
			createCollectionPoint(ctx)
		} else {
			ctx.Error("Method not allowed", fasthttp.StatusMethodNotAllowed)
		}
	case "/post-collection-point":
		if string(ctx.Method()) == fasthttp.MethodPost {
			postCollectionPoint(ctx)
		} else {
			ctx.Error("Method not allowed", fasthttp.StatusMethodNotAllowed)
		}
	case "/update-collection-point":
		if string(ctx.Method()) == fasthttp.MethodPost {
			updateCollectionPoint(ctx)
		} else {
			ctx.Error("Method not allowed", fasthttp.StatusMethodNotAllowed)
		}
	case "/get-collection-points":
		if string(ctx.Method()) == fasthttp.MethodGet {
			getCollectionPoints(ctx)
		} else {
			ctx.Error("Method not allowed", fasthttp.StatusMethodNotAllowed)
		}
	default:
		ctx.Error("Unsupported path", fasthttp.StatusNotFound)
	}
}

func packageRegister(ctx *fasthttp.RequestCtx) {
	var data DeveloperDetails
	if err := json.Unmarshal(ctx.PostBody(), &data); err != nil {
		ctx.Error(err.Error(), fasthttp.StatusBadRequest)
		return
	}

	// Generate secret and token
	secret := uuid.Must(uuid.NewV4()).String()
	token := uuid.Must(uuid.NewV4()).String()

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

	// Insert data into MongoDB
	devCollection := mongoClient.Database(DatabaseName).Collection(CollectionDev)
	insertResult, err := devCollection.InsertOne(ctx, developerData)
	if err != nil {
		ctx.Error("Failed to insert developer details", fasthttp.StatusInternalServerError)
		return
	}

	// Insert data into organisation collection
	orgData := bson.M{
		"organisation_name":    data.OrganisationName,
		"developer_email":      data.DeveloperEmail,
		"developer_details_id": insertResult.InsertedID,
		"registered_at":        time.Now(),
	}
	orgCollection := mongoClient.Database(DatabaseName).Collection(CollectionOrg)
	_, err = orgCollection.InsertOne(ctx, orgData)
	if err != nil {
		ctx.Error("Failed to insert organisation details", fasthttp.StatusInternalServerError)
		return
	}

	response := map[string]string{
		"secret": secret,
		"token":  token,
	}
	responseBody, _ := json.Marshal(response)
	ctx.SetContentType("application/json")
	ctx.SetStatusCode(fasthttp.StatusOK)
	ctx.SetBody(responseBody)
}

func createCollectionPoint(ctx *fasthttp.RequestCtx) {
	var data CollectionPointRequest
	if err := json.Unmarshal(ctx.PostBody(), &data); err != nil {
		ctx.Error(err.Error(), fasthttp.StatusBadRequest)
		return
	}

	// Verify secret and token
	devCollection := mongoClient.Database(DatabaseName).Collection(CollectionDev)
	var developer bson.M
	err := devCollection.FindOne(ctx, bson.M{"secret": data.Secret, "token": data.Token}).Decode(&developer)
	if err != nil {
		ctx.Error("Invalid secret or token", fasthttp.StatusUnauthorized)
		return
	}

	// Define YAML template
	yamlTemplate := map[string]interface{}{
		"version": "1.0",
		"company": map[string]interface{}{
			"name":       "Your Company Name",
			"website":    "https://www.yourcompanywebsite.com",
			"company_id": "12345",
		},
		"applications": []interface{}{
			map[string]interface{}{
				"application": map[string]interface{}{
					"application_id": "app1",
					"type":           "Mobile",
					"collection_points": []interface{}{
						map[string]interface{}{
							"collection_point": map[string]interface{}{
								"collection_point_id": "cp1",
								"cp_name":             "Collection Point 1",
								"cp_url":              "https://www.collectionpoint1.com",
								"cp_status":           "active",
								"data_elements": []interface{}{
									map[string]interface{}{
										"data_element":                   "home_address",
										"data_element_title":             "Home Address",
										"data_element_description":       "One line description of home address field",
										"data_element_collection_status": "active",
										"expiry":                         "90 days",
										"cross_border":                   false,
										"data_principal":                 false,
										"sensitive":                      true,
										"encrypted":                      true,
										"retention_period":               "5 years",
										"data_owner":                     "Customer Service Department",
										"legal_basis":                    "Consent",
										"purposes": []interface{}{
											map[string]interface{}{
												"purpose_id":          "p1",
												"purpose_description": "Purpose description for home address",
												"purpose_language":    "EN",
											},
											map[string]interface{}{
												"purpose_id":          "p2",
												"purpose_description": "Another purpose description for home address",
												"purpose_language":    "EN",
											},
										},
									},
									map[string]interface{}{
										"data_element":                   "phone_number",
										"data_element_title":             "Phone Number",
										"data_element_description":       "One line description of phone number field",
										"data_element_collection_status": "inactive",
										"expiry":                         "30 days",
										"cross_border":                   true,
										"data_principal":                 true,
										"sensitive":                      false,
										"encrypted":                      false,
										"retention_period":               "1 year",
										"data_owner":                     "Marketing Department",
										"legal_basis":                    "Legitimate Interest",
										"purposes": []interface{}{
											map[string]interface{}{
												"purpose_id":          "p3",
												"purpose_description": "Purpose description for phone number",
												"purpose_language":    "EN",
											},
										},
									},
								},
							},
						},
					},
				},
			},
		},
	}

	yamlData, err := yaml.Marshal(yamlTemplate)
	if err != nil {
		ctx.Error("Failed to generate YAML template", fasthttp.StatusInternalServerError)
		return
	}

	ctx.SetContentType("application/x-yaml")
	ctx.SetStatusCode(fasthttp.StatusOK)
	ctx.SetBody(yamlData)
}

func postCollectionPoint(ctx *fasthttp.RequestCtx) {
	var collectionPoint CollectionPoint
	if err := json.Unmarshal(ctx.PostBody(), &collectionPoint); err != nil {
		ctx.Error(err.Error(), fasthttp.StatusBadRequest)
		return
	}

	collection := mongoClient.Database(DatabaseName).Collection(CollectionCP)
	_, err := collection.InsertOne(ctx, collectionPoint)
	if err != nil {
		ctx.Error("Failed to insert collection point", fasthttp.StatusInternalServerError)
		return
	}

	ctx.SetStatusCode(fasthttp.StatusOK)
}

func updateCollectionPoint(ctx *fasthttp.RequestCtx) {
	var collectionPoint CollectionPoint
	if err := json.Unmarshal(ctx.PostBody(), &collectionPoint); err != nil {
		ctx.Error(err.Error(), fasthttp.StatusBadRequest)
		return
	}

	collection := mongoClient.Database(DatabaseName).Collection(CollectionCP)
	filter := bson.M{"collection_point_id": collectionPoint.CollectionPointID}
	update := bson.M{"$set": collectionPoint}

	_, err := collection.UpdateOne(ctx, filter, update)
	if err != nil {
		ctx.Error("Failed to update collection point", fasthttp.StatusInternalServerError)
		return
	}

	ctx.SetStatusCode(fasthttp.StatusOK)
}

func getCollectionPoints(ctx *fasthttp.RequestCtx) {
	collection := mongoClient.Database(DatabaseName).Collection(CollectionCP)

	cursor, err := collection.Find(ctx, bson.M{})
	if err != nil {
		ctx.Error("Failed to retrieve collection points", fasthttp.StatusInternalServerError)
		return
	}
	defer cursor.Close(ctx)

	var collectionPoints []CollectionPoint
	if err := cursor.All(ctx, &collectionPoints); err != nil {
		ctx.Error("Failed to decode collection points", fasthttp.StatusInternalServerError)
		return
	}

	responseBody, err := json.Marshal(collectionPoints)
	if err != nil {
		ctx.Error("Failed to marshal collection points", fasthttp.StatusInternalServerError)
		return
	}

	ctx.SetContentType("application/json")
	ctx.SetStatusCode(fasthttp.StatusOK)
	ctx.SetBody(responseBody)
}
