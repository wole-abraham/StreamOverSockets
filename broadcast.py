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
    """
    Viewer endpoint: attach relayed latest_video to a new RTCPeerConnection
    and return an SDP answer. Avoids transceiver direction None errors
    by adding a sendonly transceiver BEFORE applying the remote offer.
    """
    global latest_video
    if latest_video is None:
        return {"error": "No live stream yet"}

    params = await request.json()
    try:
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    except Exception as e:
        return {"error": f"invalid offer: {e}"}

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

    try:
        # 1) Create a transceiver that explicitly says server will SEND video
        #    (browser's offer will be recvonly). Adding this BEFORE applying offer
        #    prevents direction None errors during answer generation.
        pc.addTransceiver("video", direction="sendonly")

        # 2) Apply the viewer's offer (remote description)
        await pc.setRemoteDescription(offer)

        # 3) Attach the relayed track so the server actually sends frames to viewer
        #    latest_video is expected to be a MediaStreamTrack (relay.subscribe(track) earlier)
        pc.addTrack(latest_video)

        # 4) Create and set local description (the answer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # 5) Return SDP answer to viewer
        return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}

    except Exception as exc:
        # Clean up and return useful error instead of crashing
        print("viewer handler error:", exc)
        try:
            await pc.close()
        except Exception:
            pass
        pcs.discard(pc)
        return {"error": f"server error: {exc}"}
