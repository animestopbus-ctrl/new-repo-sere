import aiohttp
from aiohttp import web
from database.db import db
import secret

async def handle_stream(request, bot_instance):
    hash_id = request.match_info['hash_id']
    link_data = await db.get_link(hash_id)
    
    if not link_data:
        return web.Response(text="❌ 404 - Link Expired or Invalid", status=404)
    
    try:
        tg_file = await bot_instance.get_file(link_data['file_id'])
        tg_url = f"https://api.telegram.org/file/bot{secret.BOT_TOKEN}/{tg_file.file_path}"
        
        # 🔥 CRITICAL: Forward the 'Range' header to support video seeking!
        req_headers = {}
        if 'Range' in request.headers:
            req_headers['Range'] = request.headers['Range']

        async with aiohttp.ClientSession() as session:
            async with session.get(tg_url, headers=req_headers) as resp:
                headers = dict(resp.headers)
                
                # 🔥 CRITICAL: This tells the browser to PLAY it inline, not download it
                headers['Content-Disposition'] = f'inline; filename="{link_data["file_name"]}"'
                
                response = web.StreamResponse(status=resp.status, headers=headers)
                await response.prepare(request)
                
                async for chunk in resp.content.iter_chunked(1024 * 64):
                    await response.write(chunk)
                
                return response
    except Exception as e:
        return web.Response(text=f"Stream Error: {str(e)}", status=500)