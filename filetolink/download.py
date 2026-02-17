import aiohttp
from aiohttp import web
from database.db import db
import secret

async def handle_download(request, bot_instance):
    hash_id = request.match_info['hash_id']
    link_data = await db.get_link(hash_id)
    
    if not link_data:
        return web.Response(text="❌ 404 - Link Expired or Invalid", status=404)
    
    try:
        # Get the actual file path from Telegram
        tg_file = await bot_instance.get_file(link_data['file_id'])
        tg_url = f"https://api.telegram.org/file/bot{secret.BOT_TOKEN}/{tg_file.file_path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(tg_url) as resp:
                headers = dict(resp.headers)
                
                # 🔥 CRITICAL: This header forces the browser to DOWNLOAD the file
                headers['Content-Disposition'] = f'attachment; filename="{link_data["file_name"]}"'
                
                # Stream the file in chunks so your server doesn't run out of RAM
                response = web.StreamResponse(status=resp.status, headers=headers)
                await response.prepare(request)
                
                async for chunk in resp.content.iter_chunked(1024 * 64):
                    await response.write(chunk)
                
                return response
    except Exception as e:
        return web.Response(text=f"Download Error: {str(e)}", status=500)