import os
import logging
from aiohttp import web
from database.db import db

# Import the Pyrogram handlers
from filetolink.download import handle_download
from filetolink.stream import handle_stream

routes = web.RouteTableDef()

def get_domain(request):
    """Detects if running on Render, Heroku, or Localhost"""
    return os.getenv("RENDER_EXTERNAL_URL", os.getenv("WEB_URL", request.host_url)).rstrip('/')

# 🟢 Keep-Alive Route (Replaces old keep_alive.py)
@routes.get('/')
async def alive(request):
    return web.Response(text="🟢 Titanium 4GB Modular Web Server is Online!")

# 🎬 The Video Player Webpage
@routes.get('/watch/{hash_id}')
async def watch_page(request):
    hash_id = request.match_info['hash_id']
    link_data = await db.get_link(hash_id)
    
    if not link_data:
        return web.Response(text="<h1>❌ 404 - Link Expired</h1><p>The self-destruct timer has triggered.</p>", content_type='text/html', status=404)
    
    file_name = link_data.get('file_name', 'Video')
    domain = get_domain(request)
    stream_url = f"{domain}/stream/{hash_id}"
    dl_url = f"{domain}/dl/{hash_id}"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{file_name}</title>
        <style>
            body {{ background-color: #0d1117; color: #fff; font-family: Arial; text-align: center; padding: 20px; }}
            video {{ max-width: 100%; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); outline: none; }}
            .container {{ max-width: 800px; margin: auto; background: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }}
            .btn {{ display: inline-block; padding: 12px 24px; margin-top: 20px; background: #238636; color: #fff; text-decoration: none; border-radius: 6px; font-weight: bold; }}
            .btn:hover {{ background: #2ea043; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2 style="color: #58a6ff;">🎬 {file_name}</h2>
            <video controls controlsList="nodownload" preload="metadata">
                <source src="{stream_url}" type="video/mp4">
            </video>
            <br>
            <a href="{dl_url}" class="btn">⬇️ Download Original File</a>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

# 📥 Route Traffic to download.py
@routes.get('/dl/{hash_id}')
async def download_route(request):
    return await handle_download(request)

# 🚀 Route Traffic to stream.py
@routes.get('/stream/{hash_id}')
async def stream_route(request):
    return await handle_stream(request)

# ⚙️ Start the Server
async def start_web_server():
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🌐 Web Server running on port {port}")
