import re
import logging
from aiohttp import web
from database.db import db
from filetolink.stream import pyro_client # Re-use the running Pyrogram client

async def handle_download(request):
    hash_id = request.match_info['hash_id']
    link_data = await db.get_link(hash_id)
    
    if not link_data:
        return web.Response(text="❌ 404 - Link Expired or Invalid", status=404)
    
    try:
        message = await pyro_client.get_messages(link_data['chat_id'], link_data['message_id'])
        if not message or message.empty:
            return web.Response(text="❌ File not found.", status=404)
        
        media = message.document or message.video or message.audio
        if not media:
            return web.Response(text="❌ No media found in this message.", status=404)

        file_size = getattr(media, 'file_size', 0)
        
        offset = 0
        limit = file_size - 1

        # 🔥 Support for IDM and Resumable Downloads
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
            'Content-Type': getattr(media, 'mime_type', 'application/octet-stream'),
            'Content-Disposition': f'attachment; filename="{link_data["file_name"]}"'
        }
        
        response = web.StreamResponse(status=206 if range_header else 200, headers=headers)
        await response.prepare(request)
        
        # 🚀 PYROGRAM CHUNK MATH
        chunk_size = 1024 * 1024
        first_chunk_no = offset // chunk_size
        first_part_cut = offset % chunk_size
        bytes_to_send = req_length

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
                
        return response

    except Exception as e:
        logging.error(f"DL Error: {e}")
        return
