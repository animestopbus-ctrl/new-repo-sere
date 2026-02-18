"""
download.py — upgraded download handler
Features:
- Proper Range and HEAD handling
- ETag & caching headers
- Disables compression for large/binary files (avoid CPU overhead)
- Uses TurboStreamer with backpressure and flow control
- Defensive logging and graceful client disconnect handling
"""

import re
import logging
import asyncio
import aiohttp
from aiohttp import web
from database.db import db
from filetolink.stream import pyro_client
from filetolink.fast import TurboStreamer

logger = logging.getLogger(__name__)

async def handle_download(request: web.Request) -> web.StreamResponse:
    """
    aiohttp handler to stream files fetched via Pyrogram (pyro_client).
    Accepts Range requests and HEAD requests.
    """
    hash_id = request.match_info.get('hash_id')
    if not hash_id:
        return web.Response(text="❌ 400 - Missing link id", status=400)

    link_data = await db.get_link(hash_id)
    if not link_data:
        return web.Response(text="❌ 404 - Link Expired or Invalid", status=404)

    try:
        # fetch message (pyrogram client wrapper). Expect message or None.
        message = await pyro_client.get_messages(link_data['chat_id'], link_data['message_id'])
        if not message or getattr(message, "empty", False):
            return web.Response(text="❌ File not found.", status=404)

        # detect media
        media = getattr(message, "document", None) or getattr(message, "video", None) or getattr(message, "audio", None)
        if not media:
            return web.Response(text="❌ No media found in this message.", status=404)

        file_size = int(getattr(media, 'file_size', 0) or 0)
        if file_size == 0:
            # fallback: if Telegram returns 0, still try to stream but warn
            logger.warning("Media file_size is 0 — streaming anyway")

        # build headers and parse Range
        offset = 0
        limit = file_size - 1 if file_size > 0 else None  # None means unknown

        range_header = request.headers.get('Range')
        if range_header and file_size > 0:
            m = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if m:
                offset = int(m.group(1))
                if m.group(2):
                    limit = int(m.group(2))
                else:
                    limit = file_size - 1

        # validate offset/limit when file_size known
        if file_size > 0 and offset >= file_size:
            return web.Response(status=416, headers={'Content-Range': f'bytes */{file_size}'})

        # HEAD request — return only headers
        is_range = bool(range_header and file_size > 0)
        
        # Determine request length
        req_length = None
        if file_size > 0 and limit is not None:
            req_length = limit - offset + 1
            if req_length < 0:
                return web.Response(status=416, headers={'Content-Range': f'bytes */{file_size}'})

        mime = getattr(media, 'mime_type', 'application/octet-stream')
        filename = link_data.get("file_name") or getattr(media, 'file_name', 'file')

        # ETag and caching helpers
        etag = f'W/"{link_data.get("message_id")}-{file_size}"' if file_size else None

        headers = {
            'Accept-Ranges': 'bytes',
            'Content-Type': mime,
            'Content-Disposition': f'attachment; filename="{filename}"',
        }
        if etag:
            headers['ETag'] = etag
        if file_size:
            headers['Content-Length'] = str(req_length) if req_length is not None else str(file_size)
            if is_range:
                headers['Content-Range'] = f'bytes {offset}-{limit}/{file_size}'

        status = 206 if is_range else 200

        # Respond to HEAD then finish
        if request.method == 'HEAD':
            return web.Response(status=status, headers=headers)

        # Create streaming response
        response = web.StreamResponse(status=status, headers=headers)

        # Disable aiohttp compression for large/binary transfers to save CPU
        # aiohttp's enable_compression(True) is default for responses; turn off explicitly for large files
        response.enable_compression(False)

        await response.prepare(request)

        # instantiate TurboStreamer and stream chunks
        streamer = TurboStreamer(
            pyro_client, 
            message, 
            offset_bytes=offset,
            limit_bytes=(limit if limit is not None else file_size - 1 if file_size else None)
        )

        try:
            bytes_sent = 0
            # backpressure: after sending N chunks call drain occasionally
            writes_since_drain = 0
            
            # 🔥 FIX: Changed to `async for` because TurboStreamer is an async generator
            async for chunk in streamer.generate():  
                # On client disconnect, aiohttp will raise ConnectionResetError / CancelledError on write
                try:
                    await response.write(chunk)
                    bytes_sent += len(chunk)
                    writes_since_drain += 1
                    # occasionally yield to event loop and allow socket buffer to drain
                    if writes_since_drain >= 8:
                        await response.drain()
                        writes_since_drain = 0
                except (ConnectionResetError, aiohttp.ClientPayloadError):
                    # client disconnected (IDM pause, etc.) — stop gracefully
                    logger.info("Client disconnected while streaming")
                    break
                    
            # attempt to finalize
            try:
                await response.write_eof()
            except (ConnectionResetError, aiohttp.ClientPayloadError):
                pass

            return response
            
        except asyncio.CancelledError:
            logger.info("Download task cancelled by server")
            raise
        except Exception as e:
            # avoid spamming logs on common connection close messages
            msg = str(e)
            if "closing transport" not in msg and "Connection lost" not in msg:
                logger.exception("Stream error")
            # try to end response if possible
            try:
                await response.write_eof()
            except Exception:
                pass
            return web.Response(status=500)
            
    except Exception as e:
        msg = str(e)
        if "closing transport" not in msg and "Connection lost" not in msg:
            logger.exception("Unhandled download error")
        return web.Response(status=500)
