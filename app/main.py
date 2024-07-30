from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import (
    register_user,
    manage_collection_point,
    manage_notice_info,
    manage_consent,
)

app = FastAPI()

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


@app.get("/")
async def read_root():
    return {"message": "Welcome bhidu"}
