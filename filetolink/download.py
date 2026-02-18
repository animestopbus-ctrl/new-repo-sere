import re
import logging
import asyncio
from aiohttp import web
from database.db import db
from filetolink.stream import pyro_client
from filetolink.fast import TurboStreamer

logger = logging.getLogger(__name__)

async def handle_download(request: web.Request) -> web.StreamResponse:
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
        filename = link_data.get("file_name") or getattr(media, 'file_name', 'file')

        offset = 0
        limit = file_size - 1
        range_header = request.headers.get('Range')
        
        # Range Request Parsing (For IDM/Resume)
        if range_header:
            m = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if m:
                offset = int(m.group(1))
                if m.group(2):
                    limit = int(m.group(2))

        # HEAD request (IDM checks file size first)
        headers = {
            'Content-Type': getattr(media, 'mime_type', 'application/octet-stream'),
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(limit - offset + 1)
        }
        if range_header:
            headers['Content-Range'] = f'bytes {offset}-{limit}/{file_size}'
            status = 206
        else:
            status = 200

        if request.method == 'HEAD':
            return web.Response(status=status, headers=headers)

        response = web.StreamResponse(status=status, headers=headers)
        response.enable_compression(False) # 🔥 Disable compression for max speed
        await response.prepare(request)

        # 🔥 INTELLIGENT WORKER SCALING 🔥
        req_size = limit - offset + 1
        # If request is small (<10MB), it's IDM asking for a piece. Use 1 worker to be safe.
        # If request is huge (>10MB), it's a browser. Use 4 workers to force speed.
        worker_count = 1 if req_size < 10 * 1024 * 1024 else 4

        # -----------------------------
        # TURBO STREAM ENGINE (RENDER SAFE TUNING)
        # -----------------------------
        streamer = TurboStreamer(
            pyro_client,
            message,
            offset_bytes=offset,
            limit_bytes=limit,
            workers=worker_count,       # Apply our smart worker logic
            # Render Free Tier Safety Settings:
            chunk_size=1024 * 1024,     # 1MB Chunks (Perfect balance)
            batch_chunks=5,             # Fetch 5MB at a time
            max_buffer_chunks=12,       # 🔥 CHANGED TO 12 TO PREVENT RAM CRASHES
        )

        async for chunk in streamer.generate():
            try:
                await response.write(chunk)
            except Exception:
                break # Client disconnected

        try:
            await response.write_eof()
        except Exception:
            pass
            
        return response

    except Exception as e:
        logger.error(f"DL Error: {e}")
        return web.Response(status=500)
