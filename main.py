from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import httpx
import uvicorn

app = FastAPI()

# Adjust these if your frontend is served from somewhere else
origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_SERVICE_URL = "http://127.0.0.1:5000"

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
        # No read timeout => None, because SSE can remain open for a while
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


@app.post("/stars")
async def create_star(star_data: dict):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{DATABASE_SERVICE_URL}/stars", json=star_data)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@app.delete("/stars/{star_id}")
async def delete_star(star_id: int):
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{DATABASE_SERVICE_URL}/stars/{star_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

# NB!!! This is dangerous. Only for admins TODO
@app.delete("/stars")
async def delete_all_stars():
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{DATABASE_SERVICE_URL}/stars")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()



if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)