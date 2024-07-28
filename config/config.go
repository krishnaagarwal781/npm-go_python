package config

import (
	"go-python/models"
	"os"
)

// LoadConfig loads configuration from environment variables.
func LoadConfig() *models.Config {
	// var cfg models.Config

	cfg := models.Config{
		MongoDBURI: os.Getenv("CONCUR_DB_URI"),
		LogLevel:  os.Getenv("LOG_LEVEL"),
		Dbname: os.Getenv("CONCUR_DB_NAME"),
		Port: os.Getenv("CONCUR_PORT"),
	}

	return &cfg
}
