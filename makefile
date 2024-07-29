.PHONY: all dev prod kill

all: dev prod kill

dev:
	@echo "Building development Docker image..."
	go build -o app . &&  docker build -f Dockerfile.dev -t concur/concur-backend:v0 && podman-compose -f docker-compose-dev.yaml up


prod:
	@echo "Building production Docker image..."
	docker build -t concur/concur-backend:v0 && podman-compose up

kill:
	podman-compose -f ./docker-compose-dev.yaml  down