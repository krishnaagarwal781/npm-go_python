package routes

import (
	"go-python/handlers"
	"go-python/models"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/cors"
	"go.mongodb.org/mongo-driver/mongo"
)

// InitializeRoutes initializes the application routes.
func InitializeRoutes(r *chi.Mux, client *mongo.Client, cfg *models.Config) {
	h := handlers.NewHandler(client, cfg)
	
	// Add cors middleware
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token"},
		ExposedHeaders:   []string{"Link"},
		AllowCredentials: true,
		MaxAge:           300, // Maximum value not ignored by any of major browsers
	}))


	r.Route("/",func(r chi.Router) {
		r.Get("/", h.Home)

		r.Post("/package-register", h.PackageRegister)
		r.Post("/create-application", h.CreateApplication)
	
		r.Post("/create-collection-point", h.CreateCollectionPoint)
		r.Post("/push-yaml", h.PushYaml)
		r.Delete("/delete-collection-point/{collection_point_id}", h.DeleteCollectionPoint)
		r.Get("/get-collection-points/{app_id}", h.GetCollectionPoints)
		r.Get("/get-notice-info/{cp_id}", h.GetNoticeInfo)
		r.Post("/post-consent-preference", h.PostConsentPreference)
	})
	

	
}
