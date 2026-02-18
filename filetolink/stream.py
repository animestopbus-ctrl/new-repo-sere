import re
import logging
import random
import asyncio
import aiohttp_jinja2
from aiohttp import web
from pyrogram import Client
import secret
from database.db import db
from filetolink.fast import TurboStreamer

logger = logging.getLogger(__name__)

# Global Client setup with high worker pool for parallel fetching
pyro_client = Client(
    "titanium_mtproto",
    api_id=secret.API_ID,
    api_hash=secret.API_HASH,
    bot_token=secret.BOT_TOKEN,
    in_memory=True,
    workers=10,  # Optimized for Render
    sleep_threshold=10
)

# 🔥 SERVE THE PRO HTML PLAYER
@aiohttp_jinja2.template('watch.html')
async def watch_page(request):
    hash_id = request.match_info.get('hash_id')
    link_data = await db.get_link(hash_id)
    
    if not link_data:
        return web.Response(text="❌ Link Expired or Invalid", status=404)
        
    return {
        'file_name': link_data['file_name'],
        'stream_url': f"/stream/{hash_id}",
        'image_url': random.choice(secret.IMAGE_LINKS), # Random Poster
        'mime_type': 'video/mp4' # Default fallback
    }

async def handle_stream(request: web.Request):
    hash_id = request.match_info.get('hash_id')
    link_data = await db.get_link(hash_id)
    if not link_data:
        return web.Response(text="❌ 404 - Link Expired", status=404)

    try:
        message = await pyro_client.get_messages(link_data['chat_id'], link_data['message_id'])
        media = getattr(message, "document", None) or getattr(message, "video", None) or getattr(message, "audio", None)
        if not media:
            return web.Response(text="❌ Media not found", status=404)

        file_size = int(getattr(media, 'file_size', 0))
        filename = link_data.get("file_name") or getattr(media, 'file_name', 'video.mp4')
        mime_type = getattr(media, "mime_type", "video/mp4")

        offset = 0
        limit = file_size - 1
        range_header = request.headers.get('Range')
        status_code = 200

        if range_header:
            m = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if m:
                offset = int(m.group(1))
                if m.group(2):
                    limit = int(m.group(2))
                status_code = 206

        # Clamp limit to file size
        if limit >= file_size:
            limit = file_size - 1

        req_length = limit - offset + 1

        headers = {
            "Content-Type": mime_type,
            "Accept-Ranges": "bytes",
            "Content-Length": str(req_length),
            "Content-Range": f"bytes {offset}-{limit}/{file_size}",
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "public, max-age=31536000", # 🔥 Cache it forever
        }

        if request.method == "HEAD":
            return web.Response(status=status_code, headers=headers)

        response = web.StreamResponse(status=status_code, headers=headers)
        response.enable_compression(False)
        await response.prepare(request)

        # Use 4 workers for Streaming to buffer video fast!
        streamer = TurboStreamer(
            pyro_client, 
            message, 
            offset, 
            limit, 
            workers=4
        )

        async for chunk in streamer.generate():
            try:
                await response.write(chunk)
            except Exception:
                break 

        try:
            await response.write_eof()
        except Exception:
            pass
            
        return response

    except Exception as e:
        logger.error(f"Stream Error: {e}")
        return web.Response(status=500)
