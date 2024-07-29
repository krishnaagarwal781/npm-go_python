# Build stage
FROM golang:latest AS builder

# Copy the application code
COPY . /concur-backend

# Set the working directory
WORKDIR /concur-backend

# Build the Golang application
RUN go build -o app .




# Production stage
FROM debian

RUN apt update && apt install -y ca-certificates

# Create a directory for the application
RUN mkdir /concur-backend

# Create a directory for the log file
RUN mkdir /concur-backend/logs

# Copy the built binary from the build stage
COPY --from=builder /concur-backend/app /concur-backend/app




# Set the working directory
WORKDIR /concur-backend


# Run the Golang application
CMD ["./app"]