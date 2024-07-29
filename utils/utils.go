package utils

import (
	"net/http"
	"strings"

	"github.com/google/uuid"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

func GenerateUUID(len int) string {
	// @TODO : fix the length of the UUID
	// Generate a new UUID of the specified length.
	uuid := uuid.New().String()

	// Remove the hyphens from the UUID.
	uuid = strings.Replace(uuid, "-", "", -1)

	return uuid[:len]

}

// GetClientIP extracts the client IP address from the request
func GetClientIP(r *http.Request) string {
	// Try to get the IP from the X-Forwarded-For header
	clientIP := r.Header.Get("X-Forwarded-For")
	if clientIP == "" {
		clientIP = r.RemoteAddr
	}

	// If the IP is in the format host:port, remove the port
	if strings.Contains(clientIP, ":") {
		clientIP = strings.Split(clientIP, ":")[0]
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

// ConvertObjectIDToString converts an object ID to a string
func ConvertObjectIDToString(id interface{}) string {
	// Convert the object ID to a string.
	IdString := id.(primitive.ObjectID).Hex()
	return IdString
}