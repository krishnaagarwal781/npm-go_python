package config

import "go-python/models"

// LoadConfig loads configuration from environment variables.
func LoadConfig() *models.Config {
	// var cfg models.Config

	cfg := models.Config{
		MongoDBURI: "mongodb+srv://samwicky:samwicky@cluster0.gmkz4bw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
		LogLevel: "debug",
		Dbname: "Concur",
	}

	return &cfg
}
