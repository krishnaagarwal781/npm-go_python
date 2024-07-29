package logger

import (
	"go-python/models"
	"os"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

// Initialize initializes the logger.
func Initialize(cfg *models.Config) {
	level, err := zerolog.ParseLevel(cfg.LogLevel)
	if err != nil {
		log.Fatal().Err(err).Msg("Invalid log level")
	}

	zerolog.SetGlobalLevel(level)

	 // Create a logger instance for all log levels
	 AppLogger := zerolog.New(os.Stderr).With().Timestamp().Logger()

	 // Set global logger
	 log.Logger = AppLogger
 
	 log.Info().Msg("Logger initialized successfully")
	
}
