#!/usr/bin/env python3
"""
Simple test server
"""
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    print("Starting test server on http://localhost:8010")
    uvicorn.run(app, host="0.0.0.0", port=8010)
