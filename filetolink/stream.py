import re
import logging
import aiohttp
from aiohttp import web
from pyrogram import Client
import secret
from database.db import db
from filetolink.fast import TurboStreamer

logger = logging.getLogger(__name__)

# ✅ KEEP CLIENT GLOBAL (VERY IMPORTANT FOR SPEED)
pyro_client = Client(
    "titanium_mtproto",
    api_id=secret.API_ID,
    api_hash=secret.API_HASH,
    bot_token=secret.BOT_TOKEN,
    in_memory=True,
    workers=8,              # 🔥 increases MTProto parallelism
    sleep_threshold=0       # prevents unnecessary sleeps
)

# -----------------------------
# STREAM HANDLER (VIDEO OPTIMIZED)
# -----------------------------
async def handle_stream(request: web.Request):

    hash_id = request.match_info.get('hash_id')
    if not hash_id:
        return web.Response(text="Bad Request", status=400)

    link_data = await db.get_link(hash_id)

    if not link_data:
        return web.Response(text="❌ 404 - Link Expired or Invalid", status=404)

    try:
        message = await pyro_client.get_messages(
            link_data['chat_id'],
            link_data['message_id']
        )

        if not message or getattr(message, "empty", False):
            return web.Response(text="❌ File not found on Telegram.", status=404)

        media = message.document or message.video or message.audio

        if not media:
            return web.Response(text="❌ No media found.", status=404)

        file_size = int(getattr(media, 'file_size', 0))

        if file_size == 0:
            logger.warning("File size unknown — streaming anyway")

        # -----------------------------
        # RANGE PARSING
        # -----------------------------
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
            return web.Response(
                status=416,
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        req_length = limit - offset + 1
        mime = getattr(media, "mime_type", None) or "video/mp4"

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(req_length),
            "Content-Range": f"bytes {offset}-{limit}/{file_size}",
            "Content-Type": mime,
            "Content-Disposition": f'inline; filename="{link_data["file_name"]}"',
            # 🔥 HUGE for streaming players
            "Cache-Control": "public, max-age=31536000",
        }

        status = 206 if range_header else 200

        # HEAD SUPPORT (players use this!)
        if request.method == "HEAD":
            return web.Response(status=status, headers=headers)

        response = web.StreamResponse(
            status=status,
            headers=headers
        )

        # 🚨 TURN OFF COMPRESSION (VERY IMPORTANT)
        response.enable_compression(False)

        await response.prepare(request)

        # -----------------------------
        # TURBO STREAM ENGINE
        # -----------------------------
        streamer = TurboStreamer(
            pyro_client,
            message,
            offset_bytes=offset,
            limit_bytes=limit,
            # 🔥 STREAMING OPTIMIZATION:
            chunk_size=512 * 1024,      # smaller chunks = faster player start
            batch_chunks=6,             # fewer Telegram RPC calls
            max_buffer_chunks=32,       # prevents RAM spikes
        )

        writes = 0

        try:
            async for chunk in streamer.generate():
                await response.write(chunk)
                writes += 1

                # backpressure relief
                if writes >= 6:
                    await response.drain()
                    writes = 0

        except (ConnectionResetError, aiohttp.ClientPayloadError):
            logger.info("Client disconnected during stream")

        except asyncio.CancelledError:
            logger.info("Streaming cancelled")

        except Exception as e:
            if "Connection lost" not in str(e):
                logger.exception("Streaming failure")

        finally:
            try:
                await response.write_eof()
            except:
                pass

        return response

    except Exception as e:
        if "Connection lost" not in str(e):
            logger.exception("Stream handler crash")
        return web.Response(status=500)
