from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import httpx
import uvicorn
import os
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional

app = FastAPI()

# Adjust these if frontend is served from somewhere else
origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database service URL
DATABASE_SERVICE_URL = "http://127.0.0.1:5000"

# JWT Authentication Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Function to extract and verify JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Verify user exists (consider querying auth service)
    return email  # You could fetch the user object if needed

# -------------------------
# Public Routes
# -------------------------

@app.get("/stars")
async def get_stars():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DATABASE_SERVICE_URL}/stars")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@app.get("/stars/stream")
async def stream_stars(request: Request):
    """
    Pass-through SSE from the DB service so the frontend
    can connect to us instead of calling the DB directly.
    """
    async def event_generator():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", f"{DATABASE_SERVICE_URL}/stars/stream") as r:
                async for line in r.aiter_lines():
                    if await request.is_disconnected():
                        break
                    yield f"{line}\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/stars/{star_id}")
async def get_star(star_id: int):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DATABASE_SERVICE_URL}/stars/{star_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

# -------------------------
# Protected Routes (Require Authentication)
# -------------------------

@app.post("/stars")
async def create_star(
    star_data: dict,
    current_user: str = Depends(get_current_user)
):
    """
    Protected: Only authenticated users can create stars.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{DATABASE_SERVICE_URL}/stars", json=star_data)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@app.delete("/stars/{star_id}")
async def delete_star(
    star_id: int,
    current_user: str = Depends(get_current_user)
):
    """
    Protected: Only authenticated users can delete stars.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{DATABASE_SERVICE_URL}/stars/{star_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@app.delete("/stars")
async def delete_all_stars(
    current_user: str = Depends(get_current_user)
):
    """
    ⚠️ Dangerous: Only authenticated users can delete all stars.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{DATABASE_SERVICE_URL}/stars")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

# -------------------------
# Run Server
# -------------------------

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
