import re
import logging
import aiohttp
from aiohttp import web
from pyrogram import Client
import secret
from database.db import db
from filetolink.fast import TurboStreamer

logger = logging.getLogger(__name__)

pyro_client = Client(
    "titanium_mtproto",
    api_id=secret.API_ID,
    api_hash=secret.API_HASH,
    bot_token=secret.BOT_TOKEN,
    in_memory=True,
    workers=8,
    sleep_threshold=0
)

async def handle_stream(request: web.Request):
    hash_id = request.match_info.get('hash_id')
    if not hash_id:
        return web.Response(text="Bad Request", status=400)

    link_data = await db.get_link(hash_id)
    if not link_data:
        return web.Response(text="❌ 404 - Link Expired or Invalid", status=404)

    try:
        message = await pyro_client.get_messages(link_data['chat_id'], link_data['message_id'])
        if not message or getattr(message, "empty", False):
            return web.Response(text="❌ File not found on Telegram.", status=404)

        media = message.document or message.video or message.audio
        if not media:
            return web.Response(text="❌ No media found.", status=404)

        file_size = int(getattr(media, 'file_size', 0))

        offset = 0
        limit = file_size - 1

        range_header = request.headers.get('Range')
        if range_header:
            match = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if match:
                offset = int(match.group(1))
                if match.group(2):
                    limit = int(match.group(2))

        if offset >= file_size:
            return web.Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})

        req_length = limit - offset + 1
        mime = getattr(media, "mime_type", None) or "video/mp4"

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(req_length),
            "Content-Range": f"bytes {offset}-{limit}/{file_size}",
            "Content-Type": mime,
            "Content-Disposition": f'inline; filename="{link_data["file_name"]}"',
            "Cache-Control": "public, max-age=31536000",
        }

        status = 206 if range_header else 200

        if request.method == "HEAD":
            return web.Response(status=status, headers=headers)

        response = web.StreamResponse(status=status, headers=headers)
        response.enable_compression(False)
        await response.prepare(request)

        # 🔥 RENDER RAM DIET: Fast startup with strict memory caps
        streamer = TurboStreamer(
            pyro_client,
            message,
            offset_bytes=offset,
            limit_bytes=limit,
            chunk_size=512 * 1024,      # 512KB chunks for instant video start
            batch_chunks=2,             # Fetch 1MB at a time
            max_buffer_chunks=16,       # Keep max 8MB in RAM per viewer
        )

        writes = 0
        try:
            async for chunk in streamer.generate():
                await response.write(chunk)
                writes += 1
                if writes >= 5:
                    await response.drain()
                    writes = 0

        except (ConnectionResetError, aiohttp.ClientPayloadError):
            pass 
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if "Connection lost" not in str(e):
                pass 
        finally:
            try:
                await response.write_eof()
            except:
                pass

        return response

    except Exception as e:
        return web.Response(status=500)
