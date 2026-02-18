import re
import logging
import asyncio
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
    workers=50,  # 🔥 Increased internal pool for TurboStreamer
    sleep_threshold=10
)

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

        offset = 0
        limit = file_size - 1
        range_header = request.headers.get('Range')

        if range_header:
            m = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if m:
                offset = int(m.group(1))
                if m.group(2):
                    limit = int(m.group(2))

        headers = {
            "Content-Type": getattr(media, "mime_type", "video/mp4"),
            "Accept-Ranges": "bytes",
            "Content-Length": str(limit - offset + 1),
            "Content-Range": f"bytes {offset}-{limit}/{file_size}",
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "public, max-age=31536000", # 🔥 Cache it forever
        }

        status = 206 if range_header else 200

        if request.method == "HEAD":
            return web.Response(status=status, headers=headers)

        response = web.StreamResponse(status=status, headers=headers)
        response.enable_compression(False)
        await response.prepare(request)

        # Use 4 workers for Streaming to buffer video fast!
        streamer = TurboStreamer(pyro_client, message, offset, limit, workers=4)

        async for chunk in streamer.generate():
            try:
                await response.write(chunk)
            except Exception:
                break 

        await response.write_eof()
        return response

    except Exception as e:
        logger.error(f"Stream Error: {e}")
        return web.Response(status=500)
