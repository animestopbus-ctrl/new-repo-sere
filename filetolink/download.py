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
    hash_id = request.match_info.get('hash_id')
    if not hash_id:
        return web.Response(text="❌ 400 - Missing link id", status=400)

    link_data = await db.get_link(hash_id)
    if not link_data:
        return web.Response(text="❌ 404 - Link Expired or Invalid", status=404)

    try:
        message = await pyro_client.get_messages(link_data['chat_id'], link_data['message_id'])
        if not message or getattr(message, "empty", False):
            return web.Response(text="❌ File not found.", status=404)

        media = getattr(message, "document", None) or getattr(message, "video", None) or getattr(message, "audio", None)
        if not media:
            return web.Response(text="❌ No media found in this message.", status=404)

        file_size = int(getattr(media, 'file_size', 0) or 0)

        offset = 0
        limit = file_size - 1 if file_size > 0 else None

        range_header = request.headers.get('Range')
        if range_header and file_size > 0:
            m = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if m:
                offset = int(m.group(1))
                if m.group(2):
                    limit = int(m.group(2))
                else:
                    limit = file_size - 1

        if file_size > 0 and offset >= file_size:
            return web.Response(status=416, headers={'Content-Range': f'bytes */{file_size}'})

        is_range = bool(range_header and file_size > 0)
        req_length = None
        if file_size > 0 and limit is not None:
            req_length = limit - offset + 1
            if req_length < 0:
                return web.Response(status=416, headers={'Content-Range': f'bytes */{file_size}'})

        mime = getattr(media, 'mime_type', 'application/octet-stream')
        filename = link_data.get("file_name") or getattr(media, 'file_name', 'file')
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

        if request.method == 'HEAD':
            return web.Response(status=status, headers=headers)

        response = web.StreamResponse(status=status, headers=headers)
        response.enable_compression(False)
        await response.prepare(request)

        # 🔥 RENDER RAM DIET: Tiny chunks and low buffer memory for IDM
        streamer = TurboStreamer(
            pyro_client, 
            message, 
            offset_bytes=offset,
            limit_bytes=(limit if limit is not None else file_size - 1 if file_size else None),
            chunk_size=1024 * 1024,
            batch_chunks=2,           # Fetch 2MB at a time
            max_buffer_chunks=8       # Keep max 8MB per connection in RAM
        )

        try:
            writes_since_drain = 0
            async for chunk in streamer.generate():  
                try:
                    await response.write(chunk)
                    writes_since_drain += 1
                    if writes_since_drain >= 5:
                        await response.drain()
                        writes_since_drain = 0
                except (ConnectionResetError, aiohttp.ClientPayloadError):
                    break
                    
            try:
                await response.write_eof()
            except:
                pass

            return response
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            msg = str(e)
            if "closing transport" not in msg and "Connection lost" not in msg:
                pass
            try:
                await response.write_eof()
            except Exception:
                pass
            return web.Response(status=500)
            
    except Exception as e:
        return web.Response(status=500)
