package database

import (
	"context"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"github.com/rs/zerolog/log"
)


func InitializeMongoClient(uri string) (*mongo.Client, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		return nil, err
	}

	// Retry logic with exponential backoff
	maxRetries := 5
	retryInterval := time.Second

	for i := 0; i < maxRetries; i++ {
		err = client.Ping(ctx, nil)
		if err == nil {
			return client, nil
		}
		log.Debug().Msgf("Attempt %d for reconnecting mongodb failed",retryInterval)
		time.Sleep(retryInterval)
		retryInterval *= 2
	}

	

	return nil, err
}


func InsertData(ctx context.Context, client *mongo.Client, database_name string, collection_name string, payload interface{}) (*mongo.InsertOneResult,error) {

	collection := client.Database(database_name).Collection(collection_name)
	result, err := collection.InsertOne(ctx, payload)
	if err != nil {
		return nil,err
	}

	return result,nil
}

func FindData(ctx context.Context, client *mongo.Client, database_name string, collection_name string, filter interface{}) (*mongo.Cursor,error) {
	
	collection := client.Database(database_name).Collection(collection_name)
	cursor, err := collection.Find(ctx, filter)
	if err != nil {
		return nil,err
	}

	return cursor,nil
}

// FindOne finds a single document in the specified collection
func FindOne(ctx context.Context, client *mongo.Client, databaseName string, collectionName string, filter interface{}) *mongo.SingleResult {
	collection := client.Database(databaseName).Collection(collectionName)
	return collection.FindOne(ctx, filter)
}

// UpdateData updates a document in the specified collection
func UpdateData(ctx context.Context, client *mongo.Client, databaseName string, collectionName string, filter interface{}, update interface{}) (*mongo.UpdateResult, error) {
	collection := client.Database(databaseName).Collection(collectionName)
	result, err := collection.UpdateOne(ctx, filter, update)
	if err != nil {
		return nil, err
	}
	return result, nil
}

func DeleteOne(ctx context.Context, client *mongo.Client, databaseName string, collectionName string, filter interface{}) (*mongo.DeleteResult, error) {
	collection := client.Database(databaseName).Collection(collectionName)
	result, err := collection.DeleteOne(ctx, filter)
	if err != nil {
		return nil, err
	}
	return result, nil
}
