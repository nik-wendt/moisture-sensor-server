from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import routes

print("Starting FastAPI server...")

origins = ["*"]

app = FastAPI(debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)
