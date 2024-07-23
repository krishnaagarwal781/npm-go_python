package main

import (
	// "context"
	"context"
	"go-python/config"
	"go-python/database"
	"go-python/logger"
	"go-python/routes"
	"net/http"

	"github.com/go-chi/chi/v5"
	// "github.com/go-chi/chi/v5/middleware"

	// "github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	// "go.mongodb.org/mongo-driver/mongo"
	// "go.mongodb.org/mongo-driver/mongo/options"
)

func main() {
	// Initialize configuration
	cfg := config.LoadConfig()

	// Initialize logger
	logger.Initialize(cfg)

	
	// Initialize MongoDB client
	client, err := database.InitializeMongoClient(cfg.MongoDBURI)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to initialize MongoDB client")
	}

	defer client.Disconnect(context.Background())

	// Initialize router
	r := chi.NewRouter()
	// r.Use(middleware.Logger)

	// Initialize routes
	routes.InitializeRoutes(r, client, cfg)

	// Start server
	log.Info().Msg("Starting server on :8080")
	if err := http.ListenAndServe(":8080", r); err != nil {
		log.Fatal().Err(err).Msg("Failed to start server")
	}
}
