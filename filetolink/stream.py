import re
import logging
from aiohttp import web
from pyrogram import Client
import secret
from database.db import db

# Initialize MTProto Client
pyro_client = Client(
    "titanium_mtproto",
    api_id=secret.API_ID,
    api_hash=secret.API_HASH,
    bot_token=secret.BOT_TOKEN,
    in_memory=True
)

async def handle_stream(request):
    hash_id = request.match_info['hash_id']
    link_data = await db.get_link(hash_id)
    
    if not link_data:
        return web.Response(text="❌ 404 - Link Expired or Invalid", status=404)
    
    try:
        message = await pyro_client.get_messages(link_data['chat_id'], link_data['message_id'])
        if not message or message.empty:
            return web.Response(text="❌ File not found on Telegram servers.", status=404)

        media = message.document or message.video or message.audio
        if not media:
            return web.Response(text="❌ No media found in this message.", status=404)

        file_size = getattr(media, 'file_size', 0)
        
        offset = 0
        limit = file_size - 1

        # Handle Browser Range Requests perfectly
        range_header = request.headers.get('Range')
        if range_header:
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                offset = int(match.group(1))
                if match.group(2):
                    limit = int(match.group(2))

        if offset >= file_size:
            return web.Response(status=416, headers={'Content-Range': f'bytes */{file_size}'})

        req_length = limit - offset + 1

        headers = {
            'Content-Range': f'bytes {offset}-{limit}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(req_length),
            'Content-Type': getattr(media, 'mime_type', 'video/mp4'),
            'Content-Disposition': f'inline; filename="{link_data["file_name"]}"'
        }

        response = web.StreamResponse(status=206 if range_header else 200, headers=headers)
        response.enable_compression()
        await response.prepare(request)

        # Telegram Chunk Math (1MB Blocks)
        chunk_size = 1048576 
        first_part_cut = offset % chunk_size
        first_chunk_no = offset // chunk_size
        bytes_to_send = req_length

        try:
            # 🚀 NATIVE PIPELINE: Instant delivery, zero RAM overhead
            async for chunk in pyro_client.stream_media(message, offset=first_chunk_no):
                if first_part_cut:
                    chunk = chunk[first_part_cut:]
                    first_part_cut = 0
                    
                if len(chunk) > bytes_to_send:
                    chunk = chunk[:bytes_to_send]
                    
                await response.write(chunk)
                
                bytes_to_send -= len(chunk)
                if bytes_to_send <= 0:
                    break
        except Exception as e:
            # Safely ignore normal browser disconnections
            if "closing transport" not in str(e) and "Connection lost" not in str(e):
                logging.error(f"Stream Write Error: {e}")
                
        return response

    except Exception as e:
        if "closing transport" not in str(e) and "Connection lost" not in str(e):
            logging.error(f"Stream Error: {e}")
        return web.Response(status=500)
