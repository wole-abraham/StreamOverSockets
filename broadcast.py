from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
    MediaStreamTrack
)
from aiortc.contrib.media import MediaRelay
import asyncio

app = FastAPI()
templates = Jinja2Templates(directory="templates")

pcs = set()
relay = MediaRelay()  # Relay helps duplicate video streams safely
latest_video = None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/offer")
async def offer(request: Request):
    """Handle the stream sender (from send.py)"""
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
        global latest_video
        print(f"Received track: {track.kind}")
        if track.kind == "video":
            latest_video = relay.subscribe(track)

        @track.on("ended")
        async def on_ended():
            print("Track ended.")
            global latest_video
            latest_video = None

    @pc.on("iceconnectionstatechange")
    def on_ice_state():
        print("Sender ICE state:", pc.iceConnectionState)
        if pc.iceConnectionState in ["failed", "closed", "disconnected"]:
            pcs.discard(pc)
            asyncio.create_task(pc.close())

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

    @pc.on("iceconnectionstatechange")
    def on_state_change():
        print("Viewer ICE state:", pc.iceConnectionState)
        if pc.iceConnectionState in ("failed", "closed", "disconnected"):
            asyncio.create_task(pc.close())
            pcs.discard(pc)

    # Add a "recvonly" transceiver for video BEFORE setting the remote description
    pc.addTransceiver("video", direction="recvonly")

    # Now apply the viewer's offer
    await pc.setRemoteDescription(offer)

    # Add the latest video track to send video to this viewer
    pc.addTrack(latest_video)

    # Create and set local description (the answer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
