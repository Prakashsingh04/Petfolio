from fastapi import FastAPI

app = FastAPI(
    title="Pet Adoption Portal API",
    version="1.0.0"
)



@app.get("/")
async def home():
    return {
        "status": "home"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }