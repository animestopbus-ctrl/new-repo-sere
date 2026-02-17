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
        # Fetch the exact message from Telegram
        message = await pyro_client.get_messages(link_data['chat_id'], link_data['message_id'])
        if not message or message.empty:
            return web.Response(text="❌ File not found.", status=404)
        
        media = message.document or message.video or message.audio
        if not media:
            return web.Response(text="❌ No media found in this message.", status=404)

        file_size = getattr(media, 'file_size', 0)
        
        headers = {
            'Content-Length': str(file_size),
            'Content-Type': getattr(media, 'mime_type', 'application/octet-stream'),
            'Content-Disposition': f'attachment; filename="{link_data["file_name"]}"' # Forces Browser to Download
        }
        
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        
        # 🚀 Stream chunks directly to user's hard drive
        async for chunk in pyro_client.stream_media(message):
            await response.write(chunk)
            
        return response

    except Exception as e:
        logging.error(f"DL Error: {e}")
        return web.Response(text=f"Download Error: {str(e)}", status=500)
