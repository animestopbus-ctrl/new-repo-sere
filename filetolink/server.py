import os
import aiohttp
from aiohttp import web
from database.db import db
import secret

routes = web.RouteTableDef()
bot_instance = None

# 🔥 1. THE KEEP-ALIVE ROUTE (Replaces keep_alive.py)
@routes.get('/')
async def alive(request):
    return web.Response(text="🟢 Titanium Streaming Engine & Web Server is Online!")

# 🔥 2. THE HTML VIDEO PLAYER UI (webpage.py logic)
@routes.get('/watch/{hash_id}')
async def watch_page(request):
    hash_id = request.match_info['hash_id']
    link_data = await db.get_link(hash_id)
    
    if not link_data:
        return web.Response(text="<h1>❌ 404 - Link Expired or Invalid</h1><blockquote>The self-destruct timer has triggered.</blockquote>", content_type='text/html', status=404)
    
    file_name = link_data.get('file_name', 'Video')
    domain = os.getenv("RENDER_EXTERNAL_URL", os.getenv("WEB_URL", request.host_url)).rstrip('/')
    stream_url = f"{domain}/stream/{hash_id}"
    dl_url = f"{domain}/dl/{hash_id}"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{file_name} - Titanium Stream</title>
        <style>
            body {{ background-color: #0d1117; color: #fff; font-family: Arial, sans-serif; text-align: center; margin: 0; padding: 20px; }}
            video {{ max-width: 100%; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); outline: none; }}
            .container {{ max-width: 800px; margin: auto; padding: 20px; background: #161b22; border-radius: 15px; border: 1px solid #30363d; }}
            .btn {{ display: inline-block; padding: 12px 24px; margin-top: 20px; background: #238636; color: #fff; text-decoration: none; border-radius: 6px; font-weight: bold; transition: 0.2s; }}
            .btn:hover {{ background: #2ea043; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2 style="color: #58a6ff;">🎬 {file_name}</h2>
            <video controls controlsList="nodownload" preload="metadata">
                <source src="{stream_url}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            <br>
            <a href="{dl_url}" class="btn">⬇️ Download Original File</a>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

# 🔥 3. THE DOWNLOAD & STREAM PROXY (download.py & stream.py logic)
async def proxy_telegram_file(request, hash_id, as_attachment=False):
    link_data = await db.get_link(hash_id)
    if not link_data:
        return web.Response(text="Expired", status=404)
    
    try:
        # Ask Telegram for the actual file path
        tg_file = await bot_instance.get_file(link_data['file_id'])
        tg_url = f"https://api.telegram.org/file/bot{secret.BOT_TOKEN}/{tg_file.file_path}"
        
        # Proxy headers to support video seeking (Byte-Ranges)
        headers = {}
        if 'Range' in request.headers:
            headers['Range'] = request.headers['Range']

        async with aiohttp.ClientSession() as session:
            async with session.get(tg_url, headers=headers) as resp:
                proxy_headers = dict(resp.headers)
                if as_attachment:
                    proxy_headers['Content-Disposition'] = f'attachment; filename="{link_data["file_name"]}"'
                
                # Stream the response directly to the user's browser
                response = web.StreamResponse(status=resp.status, headers=proxy_headers)
                await response.prepare(request)
                
                async for chunk in resp.content.iter_chunked(1024 * 64):
                    await response.write(chunk)
                
                return response
    except Exception as e:
        return web.Response(text=f"Stream Error: {str(e)}", status=500)

@routes.get('/dl/{hash_id}')
async def download_route(request):
    return await proxy_telegram_file(request, request.match_info['hash_id'], as_attachment=True)

@routes.get('/stream/{hash_id}')
async def stream_route(request):
    return await proxy_telegram_file(request, request.match_info['hash_id'], as_attachment=False)

# 🔥 SERVER BOOTSTRAP
async def start_web_server(bot):
    global bot_instance
    bot_instance = bot
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Heroku & Render dynamically inject the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🌐 Titanium Web Server running on port {port}")