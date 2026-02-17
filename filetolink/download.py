import re
import logging
import aiohttp
from aiohttp import web
from database.db import db
from filetolink.stream import pyro_client
from filetolink.fast import ParallelStreamer # 🔥 Turbo Engine

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
        
        streamer = ParallelStreamer(pyro_client, message, offset, limit, workers=15, prefetch_mb=50)
        
        # 🔥 FIX: Gracefully handle Download Managers pausing/resuming
        try:
            async for chunk in streamer.generate():
                await response.write(chunk)
        except (ConnectionResetError, aiohttp.ClientPayloadError, aiohttp.ClientDisconnectedError):
            pass
        except Exception as e:
            if "closing transport" not in str(e) and "Connection lost" not in str(e):
                logging.error(f"DL Write Error: {str(e)}")
                
        return response

    except Exception as e:
        if "closing transport" not in str(e) and "Connection lost" not in str(e):
            logging.error(f"DL Error: {str(e)}")
        return web.Response(status=500)
