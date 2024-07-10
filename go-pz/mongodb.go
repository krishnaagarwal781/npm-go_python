package main

import (
	"context"
	"log"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

var (
	developerDetailsCollection *mongo.Collection
	organisationCollection     *mongo.Collection
	collectionPointCollection  *mongo.Collection
)

func initMongoDB() {
	// Initialize MongoDB collections
	clientOptions := options.Client().ApplyURI("mongodb+srv://your_connection_string")
	client, err := mongo.Connect(context.Background(), clientOptions)
	if err != nil {
		log.Fatal(err)
	}

	db := client.Database("python-go")
	developerDetailsCollection = db.Collection("developer_details")
	organisationCollection = db.Collection("organisation_details")
	collectionPointCollection = db.Collection("collection_points")
}

func InsertDeveloperDetails(data map[string]interface{}) error {
	_, err := developerDetailsCollection.InsertOne(context.Background(), data)
	return err
}

func InsertOrganisationDetails(orgName, devEmail, secret string) error {
	data := map[string]interface{}{
		"organisation_name":    orgName,
		"developer_email":      devEmail,
		"developer_details_id": "", // Update with developer ID
		"registered_at":        time.Now().UTC(),
	}

	_, err := organisationCollection.InsertOne(context.Background(), data)
	return err
}

func VerifyDeveloper(secret, token string) (map[string]interface{}, error) {
	filter := map[string]string{
		"secret": secret,
		"token":  token,
	}

	var developer map[string]interface{}
	err := developerDetailsCollection.FindOne(context.Background(), filter).Decode(&developer)
	return developer, err
}

func SaveCollectionPointData(data CollectionPointRequest) error {
	// Implement logic to save collection point data to MongoDB
	collectionPoint := map[string]interface{}{
		"secret": data.Secret,
		"token":  data.Token,
		// Add other fields as needed
	}

	_, err := collectionPointCollection.InsertOne(context.Background(), collectionPoint)
	return err
}

func UpdateCollectionPointData(data CollectionPointUpdateRequest) error {
	// Implement logic to update collection point data in MongoDB
	filter := map[string]interface{}{
		"collection_point_id": data.CpID,
	}

	update := map[string]interface{}{
		"$set": map[string]interface{}{
			"cp_name":   data.CpName,
			"cp_url":    data.CpURL,
			"cp_status": data.CpStatus,
			// Update other fields as needed
		},
	}

	_, err := collectionPointCollection.UpdateOne(context.Background(), filter, update)
	return err
}

func RetrieveCollectionPoints() ([]CollectionPoint, error) {
	// Implement logic to retrieve collection points from MongoDB
	var collectionPoints []CollectionPoint

	cursor, err := collectionPointCollection.Find(context.Background(), map[string]interface{}{})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(context.Background())

	for cursor.Next(context.Background()) {
		var cp CollectionPoint
		err := cursor.Decode(&cp)
		if err != nil {
			return nil, err
		}
		collectionPoints = append(collectionPoints, cp)
	}

	if err := cursor.Err(); err != nil {
		return nil, err
	}

	return collectionPoints, nil
}
