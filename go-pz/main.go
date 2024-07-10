package main

import (
	"log"
	"net/http"

	"github.com/gorilla/mux"
)

func main() {
	// Initialize MongoDB connection
	initMongoDB()

	// Initialize router
	router := mux.NewRouter()

	// Define routes
	router.HandleFunc("/package-register", PackageRegisterHandler).Methods("POST")
	router.HandleFunc("/create-collection-point", CreateCollectionPointHandler).Methods("POST")
	router.HandleFunc("/post-collection-point", PostCollectionPointHandler).Methods("POST")
	router.HandleFunc("/update-collection-point", UpdateCollectionPointHandler).Methods("POST")
	router.HandleFunc("/get-collection-points", GetCollectionPointsHandler).Methods("GET")

	// Start server
	log.Println("Starting server on port 8080...")
	log.Fatal(http.ListenAndServe(":8080", router))
}
