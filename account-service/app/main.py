from fastapi import FastAPI
from .routes import accounts, admin

app = FastAPI(title="Account Service")

app.include_router(accounts.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {"message": "Account service running "}