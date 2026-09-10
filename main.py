import asyncio
import json
from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import RedirectResponse
import httpx

app = FastAPI()

PORTAL_URL = "http://app.ttt5.me/stalker_portal/server/load.php"
BASE_PORTAL_ROOT = "http://app.ttt5.me/stalker_portal/"
MAC = "00:1A:79:69:1B:0D"
SN = "E4C40B59502DD"
UID = "02015E6F2FB2DC0CF4EA368AF0E2D304B8F77B34F061E2FFB53087BE68AE42E3"
RANDOM = "8e665b1c483f1fb64477d7f647d6990171388e7d"

TELEGRAM_GROUP = "https://t.me/+2lWVU6CKQsVkMWRi"
STREAM_KEY = "TvZaTak"
STUB_VIDEO_URL = "https://github.com/brawltop8599-boop/ads-stub/raw/refs/heads/main/v.mp4?password=TvZaTak"

cachedChannels = []
cachedHeaders = None
cachedToken = ""
sessionTime = 0

async def get_valid_session():
    global cachedHeaders, cachedToken, sessionTime
    loop = asyncio.get_event_loop()
    now = loop.time() * 1000
    
    if cachedHeaders and cachedToken and (now - sessionTime < 300000):
        return cachedHeaders, cachedToken

    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "X-User-Agent": "Model: MAG250; Link: WiFi",
        "Referer": "http://app.ttt5.me/stalker_portal/c/index.html",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Pragma": "no-cache",
        "Cookie": f"mac={MAC}; stb_lang=en; timezone=Europe/London"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.get(BASE_PORTAL_ROOT, headers=headers)
            await client.get(f"{BASE_PORTAL_ROOT}c/xpcom.common.js", headers=headers)
            await client.get(f"{BASE_PORTAL_ROOT}c/version.js", headers=headers)
        except Exception:
            pass

        token = ""
        try:
            hs_url = f"{PORTAL_URL}?type=stb&action=handshake&token=&JsHttpRequest=1-xml"
            hs_res = await client.get(hs_url, headers=headers)
            hs_data = hs_res.json()
            token = hs_data.get("js", {}).get("token") or hs_data.get("token") or ""

            if token:
                headers["Authorization"] = f"Bearer {token}"
                headers["Cookie"] += f"; token={token}"

            timestamp = int(asyncio.get_event_loop().time())
            metrics = json.dumps({
                "type": "stb", "model": "MAG254", "mac": MAC, "sn": SN, "uid": UID, "random": RANDOM
            })
            
            prof_url = f"{PORTAL_URL}?type=stb&action=get_profile&JsHttpRequest=1-xml&hd=1&ver=ImageDescription: 0.2.18-r23-250; ImageDate: Thu Sep 13 11:31:16 EEST 2018; PORTAL version: 5.3.0; API Version: JS API version: 343; STB API version: 146; Player Engine version: 0x58c&num_banks=2&sn={SN}&stb_type=MAG250&client_type=STB&image_version=218&video_out=hdmi&device_id=C85AAEF009B329C5C5CB3DD289E28E80F7BA0FB3546C241D9513689EB3E5DD72&device_id2=C85AAEF009B329C5C5CB3DD289E28E80F7BA0FB3546C241D9513689EB3E5DD72&signature=D4C50DE5E0F6520D7448C2A4E7824AD6329E1E1BFE90F9ECFDBDA95843156381&auth_second_step=1&hw_version=1.7-BD-00&not_valid_token=0&metrics={metrics}&hw_version_2=19d5c2a96e9ea34760bef840e09c7d7613ab6d70&timestamp={timestamp}&api_signature=262&prehash=9b45f580e912fc6c062369b891f5fb6e1266c893"
            
            await client.get(prof_url, headers=headers)
            await client.get(f"{PORTAL_URL}?type=account_info&action=get_main_info&JsHttpRequest=1-xml", headers=headers)

            cachedHeaders = headers
            cachedToken = token
            sessionTime = now
        except Exception:
            pass

    return cachedHeaders or headers, cachedToken

async def update_channels_list():
    global cachedChannels
    try:
        headers, _ = await get_valid_session()
        genres_map = {}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                genres_res = await client.get(f"{PORTAL_URL}?type=itv&action=get_genres&JsHttpRequest=1-xml", headers=headers)
                genres_json = genres_res.json()
                genres_data = genres_json.get("js") if isinstance(genres_json.get("js"), list) else genres_json.get("js", {}).get("data", [])
                for g in genres_data:
                    if g.get("id") and g.get("title"):
                        genres_map[g["id"]] = g["title"]
            except Exception:
                pass

            channels_urls = [
                f"{PORTAL_URL}?type=itv&action=get_all_channels&JsHttpRequest=1-xml",
                f"{PORTAL_URL}?type=itv&action=get_all_channels&genre=*&JsHttpRequest=1-xml"
            ]

            raw_channels = []
            for c_url in channels_urls:
                try:
                    res = await client.get(c_url, headers=headers)
                    res_json = res.json()
                    js_data = res_json.get("js")
                    data = js_data if isinstance(js_data, list) else (js_data.get("data") or js_data.get("channels") or [])
                    if isinstance(data, list) and len(data) > 0:
                        raw_channels = data
                        break
                except Exception:
                    pass

            seen = set()
            new_channels = []
            for ch in raw_channels:
                cmd = ch.get("cmd")
                if cmd and cmd not in seen:
                    seen.add(cmd)
                    genre_id = ch.get("tv_genre_id") or ch.get("genre_id") or ""
                    new_channels.append({
                        "name": ch.get("name") or ch.get("title") or "Kanal",
                        "cmd": cmd,
                        "timeshift": ch.get("timeshift", 0),
                        "group_title": genres_map.get(genre_id, "Umumiy")
                    })

            if new_channels:
                cachedChannels = new_channels
    except Exception:
        pass

@app.get("/")
async def root():
    return RedirectResponse(TELEGRAM_GROUP, status_code=302)

@app.get("/st.m3u8")
async def st_m3u8():
    empty_playlist = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-ENDLIST\n"
    return Response(content=empty_playlist, media_type="audio/x-mpegurl")

@app.get("/playlist.json")
async def playlist_json(request: httpx.Request):
    if not cachedChannels:
        await update_channels_list()
    base_url = str(request.base_url).rstrip("/")
    result = [
        {
            "name": ch["name"],
            "url": f"{base_url}/stream/{idx}?key={STREAM_KEY}",
            "group_title": ch["group_title"]
        }
        for idx, ch in enumerate(cachedChannels)
    ]
    return result

@app.get("/pl.m3u8")
async def playlist_m3u(request: httpx.Request):
    if not cachedChannels:
        await update_channels_list()
    base_url = str(request.base_url).rstrip("/")
    m3u = ["#EXTM3U"]
    for idx, ch in enumerate(cachedChannels):
        shift = f' tvg-shift="{ch["timeshift"]}" catchup="default" catchup-days="3"' if ch["timeshift"] else ""
        group = f' group-title="{ch["group_title"]}"' if ch["group_title"] else ""
        m3u.append(f"#EXTINF:-1{group}{shift},{ch['name']}")
        m3u.append(f"{base_url}/stream/{idx}?key={STREAM_KEY}")
    return Response(content="\n".join(m3u), media_type="audio/x-mpegurl")

@app.get("/stream/{idx}")
async def stream(idx: int, key: str = ""):
    if key != STREAM_KEY:
        return RedirectResponse(STUB_VIDEO_URL, status_code=302)

    if not cachedChannels:
        await update_channels_list()

    if idx < 0 or idx >= len(cachedChannels):
        return RedirectResponse(STUB_VIDEO_URL, status_code=302)

    target = cachedChannels[idx]
    stream_url = ""

    try:
        headers, token = await get_valid_session()
        link_url = f"{PORTAL_URL}?type=itv&action=create_link&cmd={import_encode(target['cmd'])}&JsHttpRequest=1-xml"
        # Для удобства кодирования параметров используем urllib.parse
        ...
