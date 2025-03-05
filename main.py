from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import httpx
import uvicorn

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

DATABASE_SERVICE_URL = "http://127.0.0.1:5000"
FILTER_SERVICE_URL = "http://127.0.0.1:7000"

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
    # Log the incoming star data for debugging
    print("Incoming star data:", star_data)

    # Send the full star data to the filter service
    async with httpx.AsyncClient() as client:
        # Forward the entire star_data to the filter service
        resp = await client.post(f"{FILTER_SERVICE_URL}/filter", json=star_data)

        # Log the response from the filter service for debugging
        print("Response from filter service:", resp.json())

        # Check if the response status code is 200 (OK)
        if resp.status_code == 200:
            # Parse the JSON response to get the status and message
            filter_response = resp.json()
            is_acceptable = filter_response.get("status")

            # If message is acceptable
            if is_acceptable:
                # Forward to database
                async with httpx.AsyncClient() as client:
                    db_resp = await client.post(
                        f"{DATABASE_SERVICE_URL}/stars", json=star_data
                    )
                if db_resp.status_code != 200:
                    raise HTTPException(
                        status_code=db_resp.status_code, detail=db_resp.text
                    )
                return db_resp.json()
            else:
                # Return the filter service's response message if message
                # is inappropriate
                return filter_response
        else:
            # Raise an exception if the filter service returns an error
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

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