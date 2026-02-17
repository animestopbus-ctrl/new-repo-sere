import re
import logging
from aiohttp import web
from pyrogram import Client
import secret
from database.db import db

# 🔥 Initialize the Pyrogram MTProto Client!
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
        # Fetch the exact message from Telegram using MTProto
        message = await pyro_client.get_messages(link_data['chat_id'], link_data['message_id'])
        if not message or message.empty:
            return web.Response(text="❌ File not found on Telegram servers.", status=404)

        media = message.document or message.video or message.audio
        if not media:
            return web.Response(text="❌ No media found in this message.", status=404)

        file_size = getattr(media, 'file_size', 0)
        
        offset = 0
        limit = file_size - 1

        # 🔥 Handle Byte-Range requests for video players
        range_header = request.headers.get('Range')
        if range_header:
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                offset = int(match.group(1))
                if match.group(2):
                    limit = int(match.group(2))

        # Failsafe if browser asks for bytes outside the file
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
        await response.prepare(request)

        # 🚀 PYROGRAM CHUNK MATH FIX (Converts Bytes to 1MB Telegram Chunks)
        chunk_size = 1024 * 1024
        first_chunk_no = offset // chunk_size
        first_part_cut = offset % chunk_size
        bytes_to_send = req_length

        async for chunk in pyro_client.stream_media(message, offset=first_chunk_no):
            # Cut off the unrequested bytes from the first chunk
            if first_part_cut:
                chunk = chunk[first_part_cut:]
                first_part_cut = 0
                
            # Stop sending if we have fulfilled the requested length
            if len(chunk) > bytes_to_send:
                chunk = chunk[:bytes_to_send]
                
            await response.write(chunk)
            
            bytes_to_send -= len(chunk)
            if bytes_to_send <= 0:
                break
                
        return response

    except Exception as e:
        logging.error(f"Stream Error: {str(e)}")
        return
