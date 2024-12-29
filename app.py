from fastapi import FastAPI
import routes

app = FastAPI(debug=True)
app.include_router(routes.router)

