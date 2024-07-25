package utils

import (
	"net/http"
	"strings"

	"github.com/google/uuid"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

func GenerateUUID(len int) string {
	// Generate a new UUID of the specified length.
	uuid := uuid.New().String()
	return uuid[:len]

}

// GetClientIP extracts the client IP address from the request
func GetClientIP(r *http.Request) string {
	// Try to get the IP from the X-Forwarded-For header
	clientIP := r.Header.Get("X-Forwarded-For")
	if clientIP == "" {
		clientIP = r.RemoteAddr
	}
	return clientIP
}

// GetHeaders extracts headers from the request
func GetHeaders(r *http.Request) map[string]string {
	headers := make(map[string]string)
	for name, values := range r.Header {
		headers[name] = strings.Join(values, ",")
	}
	return headers
}

func ConvertObjectIDToString(id interface{}) string {
	// Convert the object ID to a string.
	IdString := id.(primitive.ObjectID).Hex()
	return IdString
}