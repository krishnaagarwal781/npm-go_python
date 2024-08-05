package database

import (
	"context"
	"errors"
	"time"

	"github.com/rs/zerolog/log"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
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

func IsAuthorised(ctx context.Context, client *mongo.Client, database_name string, collection_name string, filter interface{}) (bool,error) {
	count,err := CountDocuments(context.Background(), client, database_name, collection_name, filter)
	if err != nil {
		return false,err
	}
	if count == 0 {
		log.Debug().Msg("Invalid org_key or org_secret")
		return false,err
	}
	return true,nil
}



func CountDocuments(ctx context.Context, client *mongo.Client, database_name string, collection_name string, filter interface{}) (int64,error) {
	collection := client.Database(database_name).Collection(collection_name)
	count, err := collection.CountDocuments(ctx, filter)
	if err != nil {
		return 0,err
	}
	return count,nil
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



func UpsertDocument(ctx context.Context, client *mongo.Client, dbName, collectionName string, filter, update bson.M) (primitive.ObjectID, bool, error) {
    collection := client.Database(dbName).Collection(collectionName)
    opts := options.FindOneAndUpdate().SetUpsert(true).SetReturnDocument(options.After)

    var result bson.M
    err := collection.FindOneAndUpdate(ctx, filter, update, opts).Decode(&result)
    if err != nil {
        if errors.Is(err, mongo.ErrNoDocuments) {
            insertResult, insertErr := collection.InsertOne(ctx, update["$set"])
            if insertErr != nil {
                return primitive.ObjectID{}, false, insertErr
            }
            return insertResult.InsertedID.(primitive.ObjectID), true, nil
        }
        return primitive.ObjectID{}, false, err
    }

    return result["_id"].(primitive.ObjectID), false, nil
}