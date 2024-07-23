
package routes

import (
	"go-python/handlers"
	"go-python/models"

	"github.com/go-chi/chi/v5"
	"go.mongodb.org/mongo-driver/mongo"
)

// InitializeRoutes initializes the application routes.
func InitializeRoutes(r *chi.Mux, client *mongo.Client, cfg *models.Config) {
	h := handlers.NewHandler(client, cfg)
	

	r.Route("/api", func(r chi.Router) {
		r.Post("/package-register", h.PackageRegister)
		r.Post("/create-application", h.CreateApplication)

		
		r.Post("/create-collection-point", h.CreateCollectionPoint)
		r.Post("/post-collection-point", h.PostCollectionPoint)
		r.Post("/update-collection-point", h.UpdateCollectionPoint)
		r.Get("/get-collection-points", h.GetCollectionPoints)
	})
}
