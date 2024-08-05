## Running code
- `docker build -f Dockerfile -t concur/concur-backend:v0`
- Update the env variables in the docker-compose file
- `docker-compose up`


## Env vars
- `CONCUR_DB_NAME` : database name for the operation
- `LOG_LEVEL` : Value of Debug shows all the debug logs, making it blank will only show error logs
- `CONCUR_DB_URI` : MongoDB uri for the operations
- `CONCUR_PORT` : Port to run the server   