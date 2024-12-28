from fastapi import FastAPI

import routes
from db import Base, engine

# Database setup
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(routes.router)
