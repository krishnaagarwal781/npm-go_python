from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.routes import (
    register_user,
    manage_collection_point,
    manage_notice_info,
    manage_consent,
)

app = FastAPI()

# Initialize the Limiter
limiter = Limiter(key_func=get_remote_address)

# Apply rate limiting to the entire app
@app.get("/")
@limiter.limit("5/minute")
async def read_root(request: Request):
    return {"message": "Welcome bhidu"}

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
