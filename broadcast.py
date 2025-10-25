from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
import asyncio

app = FastAPI()
templates = Jinja2Templates(directory="templates")

pcs = set()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer

from aiortc import MediaStreamTrack

latest_video = None

@app.post("/offer")
async def offer(request: Request):
    global latest_video
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    config = RTCConfiguration(iceServers=[
        RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
        RTCIceServer(urls=["turn:69.62.122.230:3478"], username="wole", credential="password123")
    ])
    pc = RTCPeerConnection(configuration=config)
    pcs.add(pc)

    @pc.on("track")
    def on_track(track):
        print(f"Received track: {track.kind}")
        if track.kind == "video":
            latest_video = track

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
@app.post("/viewer")
async def viewer(request: Request):
    global latest_video
    if latest_video is None:
        return {"error": "No live stream yet"}

    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    config = RTCConfiguration(iceServers=[
        RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
        RTCIceServer(urls=["turn:69.62.122.230:3478"], username="wole", credential="password123")
    ])
    pc = RTCPeerConnection(configuration=config)
    pcs.add(pc)

    pc.addTrack(latest_video)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}