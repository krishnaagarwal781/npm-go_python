package config

import "go-python/models"

// LoadConfig loads configuration from environment variables.
func LoadConfig() *models.Config {
	// var cfg models.Config

	cfg := models.Config{
		MongoDBURI: "",
		LogLevel: "debug",
		Dbname: "Concur",
	}

	return &cfg
}
