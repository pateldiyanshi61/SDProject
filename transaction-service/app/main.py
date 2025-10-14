from fastapi import FastAPI
from .routes import transactions

app = FastAPI(title="Transaction Service")

app.include_router(transactions.router)

@app.get("/")
def root():
    return {"message": "Transaction service running "}