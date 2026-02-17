import os
import logging
import asyncio
import json
from aiohttp import web
from database.db import db

# Import the Pyrogram handlers
from filetolink.download import handle_download
from filetolink.stream import handle_stream

routes = web.RouteTableDef()

def get_domain(request):
    """Safely detects if running on Render, Heroku, or Localhost in AIOHTTP"""
    fallback = f"{request.scheme}://{request.host}"
    return os.getenv("RENDER_EXTERNAL_URL", os.getenv("WEB_URL", fallback)).rstrip('/')

# ================= THE ULTIMATE HTML UI =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>THE UPDATED GUYS | {{FILE_NAME}}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://vjs.zencdn.net/8.3.0/video-js.css" />
    <script src="https://unpkg.com/lucide@latest"></script>

    <style>
        :root {
            --bg-primary: rgb(2, 6, 23);
            --bg-secondary: rgb(30, 41, 59);
            --bg-glass: rgba(15, 23, 42, 0.6);
            --bg-glass-dark: rgba(2, 6, 23, 0.95);
            --accent-rose: rgb(244, 63, 94);
            --accent-rose-light: rgb(248, 113, 113);
            --accent-blue: rgb(37, 99, 235);
            --accent-amber: rgb(251, 191, 36);
            --text-primary: rgb(248, 250, 252);
            --text-secondary: rgb(203, 213, 225);
            --text-muted: rgb(148, 163, 184);
            --border-subtle: rgba(255, 255, 255, 0.05);
            --border-normal: rgba(255, 255, 255, 0.1);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: "Inter", sans-serif; background: linear-gradient(to bottom, var(--bg-primary), #0a0e1a); color: var(--text-primary); min-height: 100vh; line-height: 1.6; }
        .header { position: fixed; top: 0; left: 0; right: 0; z-index: 1000; background: var(--bg-glass-dark); backdrop-filter: blur(20px); border-bottom: 1px solid var(--border-subtle); }
        .header-content { max-width: 1100px; margin: 0 auto; padding: 1rem 1.5rem; display: flex; align-items: center; justify-content: space-between; }
        .logo { font-family: "JetBrains Mono", monospace; font-size: 1.5rem; font-weight: 800; background: linear-gradient(135deg, var(--accent-rose), var(--accent-amber)); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; text-decoration: none; display: inline-block; }
        .nav { display: flex; gap: 2rem; }
        .nav a { color: var(--text-secondary); text-decoration: none; font-size: 0.875rem; font-weight: 500; transition: color 0.2s; }
        .nav a:hover { color: var(--accent-rose); }
        .mobile-menu { display: none; background: none; border: none; color: var(--text-primary); cursor: pointer; }
        .slogan { text-align: center; padding: 6.5rem 1.5rem 0.5rem; font-size: 1rem; font-weight: 600; letter-spacing: 0.5px; }
        .slogan-text { color: var(--text-secondary); }
        .slogan-highlight { background: linear-gradient(135deg, var(--accent-rose), var(--accent-amber)); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
        .container { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem 3rem; }
        .player-wrapper { margin-bottom: 1.5rem; border-radius: 16px; overflow: hidden; background: var(--bg-secondary); border: 1px solid var(--border-subtle); box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4); }
        .video-container { position: relative; width: 100%; padding-bottom: 56.25%; background: #000; overflow: hidden; }
        .video-container video { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; }
        .info-card { background: var(--bg-glass); backdrop-filter: blur(20px); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 1.75rem; margin-bottom: 1.5rem; }
        .file-title { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin-bottom: 1rem; line-height: 1.4; word-break: break-word; }
        .file-meta { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
        .meta-tag { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.375rem 0.875rem; background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.2); border-radius: 6px; color: var(--accent-rose); font-size: 0.8125rem; font-weight: 600; }
        .actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; }
        .btn { display: flex; align-items: center; justify-content: center; gap: 0.625rem; padding: 0.875rem 1.25rem; background: var(--bg-secondary); border: 1px solid var(--border-normal); border-radius: 8px; color: var(--text-primary); font-size: 0.875rem; font-weight: 600; text-decoration: none; cursor: pointer; transition: all 0.2s; }
        .btn:hover { background: rgba(244, 63, 94, 0.1); border-color: var(--accent-rose); transform: translateY(-1px); }
        .btn-primary { background: linear-gradient(135deg, var(--accent-rose), rgb(225, 29, 72)); border-color: transparent; }
        .btn-primary:hover { box-shadow: 0 8px 20px rgba(244, 63, 94, 0.3); }
        .btn svg { width: 18px; height: 18px; }
        .btn img { width: 18px; height: 18px; }
        .dropdown { position: relative; }
        .dropdown-menu { position: absolute; bottom: calc(100% + 0.5rem); right: 0; min-width: 200px; max-width: 280px; max-height: 60vh; overflow-y: auto; background: var(--bg-glass-dark); backdrop-filter: blur(20px); border: 1px solid var(--border-normal); border-radius: 8px; padding: 0.5rem; opacity: 0; visibility: hidden; transform: translateY(10px); transition: all 0.2s; z-index: 100; }
        .dropdown-menu.active { opacity: 1; visibility: visible; transform: translateY(0); }
        .dropdown-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; }
        .player-link { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.625rem; background: rgba(30, 41, 59, 0.4); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-secondary); text-decoration: none; font-size: 0.8125rem; font-weight: 500; transition: all 0.2s; }
        .player-link img { width: 16px; height: 16px; flex-shrink: 0; }
        .player-link:hover { background: rgba(244, 63, 94, 0.1); border-color: var(--accent-rose); color: var(--accent-rose); }
        .cards-section { margin: 3rem 0; }
        .section-header { text-align: center; margin-bottom: 2.5rem; }
        .section-title { font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem; background: linear-gradient(135deg, var(--accent-rose), var(--accent-amber)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .section-subtitle { color: var(--text-muted); }
        .cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
        .card { background: var(--bg-glass); backdrop-filter: blur(20px); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 2rem; transition: all 0.3s; }
        .card:hover { border-color: var(--accent-rose); transform: translateY(-4px); box-shadow: 0 12px 40px rgba(244, 63, 94, 0.2); }
        .card-icon { width: 48px; height: 48px; background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-bottom: 1.25rem; }
        .card-icon svg { color: var(--accent-rose); }
        .card h3 { font-size: 1.25rem; font-weight: 700; margin-bottom: 0.75rem; }
        .card p { color: var(--text-secondary); font-size: 0.875rem; line-height: 1.6; margin-bottom: 1.5rem; }
        .card-links { display: flex; flex-direction: column; gap: 0.5rem; }
        .card-link { display: flex; align-items: center; justify-content: space-between; padding: 0.625rem 0.875rem; background: rgba(30, 41, 59, 0.4); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-secondary); text-decoration: none; font-size: 0.8125rem; font-weight: 500; transition: all 0.2s; }
        .card-link:hover { background: rgba(244, 63, 94, 0.1); border-color: var(--accent-rose); color: var(--accent-rose); }
        .footer { text-align: center; padding: 2.5rem 1.5rem; border-top: 1px solid var(--border-subtle); color: var(--text-muted); font-size: 0.875rem; }
        .footer a { color: var(--accent-rose); text-decoration: none; font-weight: 600; }
        .aspect-dropdown { position: absolute; bottom: calc(100% + 10px); right: 0; min-width: 180px; background: var(--bg-glass-dark); backdrop-filter: blur(20px); border: 1px solid var(--border-normal); border-radius: 8px; padding: 0.5rem; opacity: 0; visibility: hidden; transform: translateY(10px); transition: all 0.2s; z-index: 1000; }
        .aspect-dropdown.active { opacity: 1; visibility: visible; transform: translateY(0); }
        .aspect-item { display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0.75rem; border-radius: 6px; color: var(--text-secondary); cursor: pointer; font-size: 0.8125rem; transition: all 0.2s; }
        .aspect-item:hover { background: rgba(244, 63, 94, 0.1); color: var(--accent-rose); }
        .aspect-item.active { background: rgba(244, 63, 94, 0.2); color: var(--accent-rose); }
        @media (max-width: 768px) {
            .nav { display: none; position: absolute; top: 100%; left: 0; right: 0; background: var(--bg-glass-dark); flex-direction: column; padding: 1rem; gap: 1rem; border-bottom: 1px solid var(--border-subtle); backdrop-filter: blur(20px); z-index: 999; animation: slideDown 0.3s ease-out; }
            .nav.active { display: flex; }
            @keyframes slideDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
            .mobile-menu { display: block; }
            .slogan { padding: 5rem 1rem 0.5rem; font-size: 0.9rem; }
            .container { padding: 1rem 1rem 2rem; }
            .player-wrapper { margin-bottom: 2rem; }
            .info-card { padding: 1.5rem; margin-bottom: 2rem; }
            .file-title { font-size: 1.2rem; margin-bottom: 0.75rem; }
            .cards-section { margin-top: 5rem !important; }
            .file-meta { margin-bottom: 1.5rem; }
            .cards-section { margin-top: 0rem; }
            .actions { grid-template-columns: 1fr; gap: 0.75rem; }
            .actions .dropdown { width: 100%; display: flex; }
            .actions .dropdown .btn { width: 100%; justify-content: center; }
            .actions .dropdown-menu { width: 100%; min-width: 250px; left: 50%; transform: translateX(-50%) translateY(10px); z-index: 1001; }
            .actions .dropdown-menu.active { transform: translateX(-50%) translateY(0); }
            .btn { padding: 0.5rem 0.75rem; font-size: 0.85rem; }
            .cards-grid { grid-template-columns: 1fr; }
            .aspect-dropdown { min-width: 120px; bottom: calc(100% + 5px); max-height: 50vh; overflow-y: auto; }
            .aspect-item { padding: 0.3rem 0.5rem; font-size: 0.65rem; }
            .aspect-item svg { width: 12px; height: 12px; }
        }
        .fade-in { animation: fadeIn 0.5s ease-out; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { background: var(--bg-secondary); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--accent-rose); }
        html { scroll-behavior: smooth; scroll-padding-top: 70px; }
        /* Video.js Custom Styles */
        .video-js { font-family: "Inter", sans-serif; }
        .vjs-big-play-button { background: var(--accent-rose) !important; border: none !important; border-radius: 50% !important; box-shadow: 0 0 20px rgba(244, 63, 94, 0.5) !important; }
        .vjs-big-play-button .vjs-icon-placeholder:before { color: var(--text-primary) !important; }
        .vjs-control-bar { background: var(--bg-glass-dark) !important; backdrop-filter: blur(20px) !important; border-top: 1px solid var(--border-subtle) !important; }
        .vjs-button > .vjs-icon-placeholder:before { color: var(--text-primary) !important; }
        .vjs-progress-control .vjs-progress-holder { background: rgba(255,255,255,0.1) !important; }
        .vjs-progress-control .vjs-load-progress { background: rgba(255,255,255,0.2) !important; }
        .vjs-progress-control .vjs-play-progress { background: var(--accent-rose) !important; }
        .vjs-slider-bar { background: var(--accent-rose) !important; }
        .vjs-time-divider, .vjs-duration, .vjs-current-time { color: var(--text-secondary) !important; }
        .vjs-menu-button-popup .vjs-menu .vjs-menu-content { background: var(--bg-glass-dark) !important; border: 1px solid var(--border-normal) !important; }
        .vjs-menu li.vjs-menu-item { color: var(--text-primary) !important; }
        .vjs-menu li.vjs-selected { background: rgba(244, 63, 94, 0.1) !important; color: var(--accent-rose) !important; }
        .vjs-quality-selector .vjs-menu-button-popup .vjs-menu .vjs-menu-title { color: var(--accent-rose) !important; }
        .theater-mode .container { max-width: none !important; padding: 0 !important; }
        .theater-mode .player-wrapper { border-radius: 0 !important; margin: 0 !important; box-shadow: none !important; }
        .theater-mode .video-container { padding-bottom: 56.25% !important; } /* Adjust as needed */
        .vjs-aspect-button, .vjs-theater-button { position: relative; }
        .vjs-aspect-button .vjs-icon-placeholder:before, .vjs-theater-button .vjs-icon-placeholder:before { content: none; }
        .vjs-aspect-button i, .vjs-theater-button i { stroke: var(--text-primary); width: 18px; height: 18px; }
        .vjs-aspect-button:hover i, .vjs-theater-button:hover i { stroke: var(--accent-rose); }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <a href="https://t.me/THEUPDATEDGUYS" class="logo"> THE UPDATED GUYS </a>
            <nav class="nav">
                <a href="#video-section">Stream</a>
                <a href="#explore">Explore</a>
                <a href="https://t.me/THEUPDATEDGUYS">Contact</a>
            </nav>
            <button class="mobile-menu">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="3" y1="12" x2="21" y2="12"></line>
                    <line x1="3" y1="6" x2="21" y2="6"></line>
                    <line x1="3" y1="18" x2="21" y2="18"></line>
                </svg>
            </button>
        </div>
    </header>

    <div class="slogan">
        <span class="slogan-text">Stream Effortlessly,</span> <span class="slogan-highlight">Anytime, Anywhere</span>
    </div>

    <div class="container">
        <section id="video-section" class="fade-in">
            <div class="player-wrapper">
                <div class="video-container">
                    <video id="player" class="video-js vjs-big-play-centered" playsinline preload="auto"></video>
                    <div class="aspect-dropdown">
                        <div class="aspect-item" data-aspect="original">Original</div>
                        <div class="aspect-item" data-aspect="16:9">16:9</div>
                        <div class="aspect-item" data-aspect="4:3">4:3</div>
                        <div class="aspect-item" data-aspect="fill">Fill</div>
                        <div class="aspect-item" data-aspect="cover">Cover</div>
                    </div>
                </div>
            </div>

            <div class="info-card">
                <h1 class="file-title">{{FILE_NAME}}</h1>
                <div class="file-meta">
                    <span class="meta-tag">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                        Now Streaming
                    </span>
                </div>

                <div class="actions">
                    <button class="btn btn-primary" onclick="blazeDownload()">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        Download Original
                    </button>
                    <button class="btn" onclick="vlc_player()">
                        <img src="https://i.postimg.cc/15TQ4y7B/vlc.png" alt="VLC" />
                        VLC Player
                    </button>
                    <button class="btn" onclick="mx_player()">
                        <img src="https://i.postimg.cc/sx4Msv4T/mx.png" alt="MX" />
                        MX Player
                    </button>

                    <div class="dropdown">
                        <button class="btn" onclick="toggleDropdown()">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="1"></circle>
                                <circle cx="19" cy="12" r="1"></circle>
                                <circle cx="5" cy="12" r="1"></circle>
                            </svg>
                            More Players
                        </button>
                        <div class="dropdown-menu" id="players-dropdown">
                            <div class="dropdown-grid">
                                <a href="#" class="player-link" onclick="playit_player()">
                                    <img src="https://i.postimg.cc/RVGWYJFF/playit.png" alt="PLAYit" />
                                    <span>PLAYit</span>
                                </a>
                                <a href="#" class="player-link" onclick="km_player()">
                                    <img src="https://i.postimg.cc/wT9tFQ9Z/km.png" alt="KM" />
                                    <span>KMPlayer</span>
                                </a>
                                <a href="#" class="player-link" onclick="s_player()">
                                    <img src="https://i.postimg.cc/XYJr6NGg/s.png" alt="S" />
                                    <span>S Player</span>
                                </a>
                                <a href="#" class="player-link" onclick="hd_player()">
                                    <img src="https://i.postimg.cc/rFT43LNh/hd.png" alt="HD" />
                                    <span>HD Player</span>
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <section id="explore" class="cards-section">
            <div class="section-header">
                <h2 class="section-title">Explore Our Universe</h2>
                <p class="section-subtitle">Discover our channels and intelligent bots</p>
            </div>
            <div class="cards-grid">
                <div class="card">
                    <div class="card-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                            <circle cx="9" cy="7" r="4"></circle>
                            <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                        </svg>
                    </div>
                    <h3>Our Channels</h3>
                    <p>Get exclusive content and real-time notifications from our premium channels</p>
                    <div class="card-links">
                        <a href="https://t.me/THEUPDATEDGUYS" class="card-link">
                            <span>The Updated Guys</span>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
                        </a>
                    </div>
                </div>
                <div class="card">
                    <div class="card-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        </svg>
                    </div>
                    <h3>Our Bots</h3>
                    <p>Intelligent bots for enhanced streaming and automated assistance</p>
                    <div class="card-links">
                        <a href="https://t.me/THEUPDATEDGUYS" class="card-link">
                            <span>Titanium Engine</span>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
                        </a>
                    </div>
                </div>
            </div>
        </section>
    </div>

    <footer class="footer">
        <p>&copy; 2026 <a href="https://t.me/THEUPDATEDGUYS">THE UPDATED GUYS</a>. All Rights Reserved.</p>
    </footer>

    <script src="https://vjs.zencdn.net/8.3.0/video.min.js"></script>

    <script>
        let originalPadding = '56.25%';

        function initPlayer() {
            const playerEl = document.getElementById('player');
            if (!playerEl) return;

            const player = videojs('player', {
                controls: true,
                autoplay: false,
                preload: 'auto',
                fluid: false,
                aspectRatio: '16:9',
                sources: [{
                    src: '{{STREAM_URL}}',
                    type: 'video/mp4' // Using raw MTProto Direct Stream
                }]
            });

            player.on('loadedmetadata', function() {
                originalPadding = (player.videoHeight() / player.videoWidth() * 100) + '%';
            });

            // Aspect Button
            const AspectButton = videojs.getComponent('Button');
            class CustomAspectButton extends AspectButton {
                constructor(player, options) {
                    super(player, options);
                    this.addClass('vjs-aspect-button');
                    this.controlText('Aspect Ratio');
                    this.el().innerHTML += '<i data-lucide="monitor"></i>';
                }
                handleClick() {
                    document.querySelector('.aspect-dropdown').classList.toggle('active');
                }
            }
            videojs.registerComponent('CustomAspectButton', CustomAspectButton);
            player.controlBar.addChild('CustomAspectButton', {}, player.controlBar.children().length - 2);

            // Theater Button
            class CustomTheaterButton extends AspectButton {
                constructor(player, options) {
                    super(player, options);
                    this.addClass('vjs-theater-button');
                    this.controlText('Theater Mode');
                    this.el().innerHTML += '<i data-lucide="theater"></i>';
                }
                handleClick() {
                    document.body.classList.toggle('theater-mode');
                }
            }
            videojs.registerComponent('CustomTheaterButton', CustomTheaterButton);
            player.controlBar.addChild('CustomTheaterButton', {}, player.controlBar.children().length - 2);

            // Aspect items logic
            document.querySelectorAll('.aspect-item').forEach(item => {
                item.addEventListener('click', () => {
                    const aspect = item.getAttribute('data-aspect');
                    const container = document.querySelector('.video-container');
                    const videoEl = player.el().querySelector('video');
                    let padding = '56.25%';
                    let fit = 'contain';

                    if (aspect === 'original') {
                        padding = originalPadding;
                    } else if (aspect === '16:9') {
                        padding = '56.25%';
                    } else if (aspect === '4:3') {
                        padding = '75%';
                    } else if (aspect === 'fill') {
                        padding = originalPadding;
                        fit = 'fill';
                    } else if (aspect === 'cover') {
                        padding = originalPadding;
                        fit = 'cover';
                    }

                    container.style.paddingBottom = padding;
                    videoEl.style.objectFit = fit;

                    document.querySelector('.aspect-item.active')?.classList.remove('active');
                    item.classList.add('active');
                    document.querySelector('.aspect-dropdown').classList.remove('active');
                });
            });

            lucide.createIcons();
        }

        function toggleDropdown() {
            document.getElementById("players-dropdown").classList.toggle("active");
        }

        function blazeDownload() {
            const a = document.createElement("a");
            a.href = "{{DL_URL}}";
            a.download = "{{FILE_NAME}}";
            a.click();
        }

        // --- EXTERNAL PLAYERS (Uses direct raw URL for dual audio & 4K MKV) ---
        function vlc_player() {
            const url = "{{STREAM_URL}}";
            const stripped = url.replace(/^https?:\/\//, "");
            window.location.href = `vlc://${stripped}`;
            setTimeout(() => {
                window.location.href = `intent:${url}#Intent;action=android.intent.action.VIEW;type=video/*;package=org.videolan.vlc;end`;
            }, 500);
        }

        function mx_player() {
            window.location.href = "intent:{{STREAM_URL}}#Intent;action=android.intent.action.VIEW;type=video/*;package=com.mxtech.videoplayer.ad;end";
        }

        function playit_player() {
            window.location.href = "playit://playerv2/video?url={{STREAM_URL}}";
        }

        function km_player() {
            window.location.href = "intent:{{STREAM_URL}}#Intent;action=android.intent.action.VIEW;type=video/*;package=com.kmplayer;end";
        }

        function s_player() {
            window.location.href = "intent:{{STREAM_URL}}#Intent;action=com.young.simple.player.playback_online;package=com.young.simple.player;end";
        }

        function hd_player() {
            window.location.href = "intent:{{STREAM_URL}}#Intent;action=android.intent.action.VIEW;type=video/*;package=uplayer.video.player;end";
        }

        document.addEventListener("click", (e) => {
            if (!e.target.closest(".dropdown")) {
                const pd = document.getElementById("players-dropdown");
                if (pd) pd.classList.remove("active");
            }
        });

        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", initPlayer);
        } else {
            initPlayer();
        }
    </script>
</body>
</html>
"""

# 🟢 Keep-Alive Route
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
    
    file_name = link_data.get('file_name', 'Unknown_Video.mp4')
    domain = get_domain(request)
    # 🔥 Using direct MTProto stream for highest speed & stability on Render
    stream_url = f"{domain}/stream/{hash_id}"
    dl_url = f"{domain}/dl/{hash_id}"

    html = HTML_TEMPLATE.replace("{{FILE_NAME}}", file_name) \
                        .replace("{{STREAM_URL}}", stream_url) \
                        .replace("{{DL_URL}}", dl_url)

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
