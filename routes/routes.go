
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
	

	r.Route("/",func(r chi.Router) {
		r.Post("/package-register", h.PackageRegister)
		r.Post("/create-application", h.CreateApplication)
	
		r.Post("/create-collection-point", h.CreateCollectionPoint)
		r.Post("/push-yaml", h.PushYaml)
		r.Delete("/delete-collection-point/{collection_point_id}", h.DeleteCollectionPoint)
		r.Get("/get-collection-points/{app_id}", h.GetCollectionPoints)
	})
	

	// r.Route("/api", func(r chi.Router) {
	// 	r.Post("/package-register", h.PackageRegister)
	// 	r.Post("/create-application", h.CreateApplication)

		
	// 	r.Post("/create-collection-point", h.CreateCollectionPoint)
	// 	r.Post("/push-yaml", h.PushYaml)
	// 	r.Delete("//delete-collection-point", h.DeleteCollectionPoint)
	// 	r.Get("/get-collection-points", h.GetCollectionPoints)
	// })

}
