import timeit
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from limits.storage import RedisStorage
from app.routes import (
    register_user,
    manage_collection_point,
    manage_notice_info,
    manage_consent,
)
from apscheduler.schedulers.background import BackgroundScheduler
from app.schemas.utils import update_contract_status_for_all

app = FastAPI()
redis_url = "redis://default:GtOhsmeCwPJsZC8B0A8R2ihcA7pDVXem@redis-11722.c44.us-east-1-2.ec2.cloud.redislabs.com:11722/0"

# Initialize the Limiter
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

scheduler = BackgroundScheduler()
scheduler.add_job(update_contract_status_for_all, "interval", seconds=10) 
scheduler.start()

def timeit_wrapper(func):
    async def wrapper(request: Request):
        start_time = timeit.default_timer()
        result = await func(request)
        end_time = timeit.default_timer()
        print(f"Execution time: {end_time - start_time} seconds")
        return result
    return wrapper

# Apply rate limiting to the entire app
@app.get("/")
@limiter.limit("5/minute")
@timeit_wrapper
async def read_root(request: Request):
    return {"message": "Welcome bhidu"}


@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

app.include_router(register_user.registerUser)
app.include_router(manage_collection_point.collectionRouter)
app.include_router(manage_notice_info.noticeRouter)
app.include_router(manage_consent.consentRouter)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
