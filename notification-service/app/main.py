from fastapi import FastAPI
from .routes import notifications

app = FastAPI(title="Notification Service")

app.include_router(notifications.router)

@app.get("/")
def root():
    return {"message": "Notification service running 📬"}