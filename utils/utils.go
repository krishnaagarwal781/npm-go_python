package utils

import (
	"github.com/google/uuid"
	"net/http"
	"strings"
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