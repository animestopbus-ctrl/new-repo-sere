import os
import logging
import asyncio
import json
from subprocess import Popen, PIPE, call
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

def get_metadata(file_path):
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', file_path]
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        data = json.loads(out)
        streams = data.get('streams', [])
        has_video = any(s['codec_type'] == 'video' for s in streams)
        has_audio = any(s['codec_type'] == 'audio' for s in streams)
        audio_tracks = [{'index': s['index'], 'label': s.get('tags', {}).get('title', f'Audio {i+1}'), 'language': s.get('tags', {}).get('language', 'und')} for i, s in enumerate(streams) if s['codec_type'] == 'audio']
        return {
            'has_video': has_video,
            'has_audio': has_audio,
            'audio_tracks': audio_tracks
        }
    except Exception as e:
        logging.error(f"Error getting metadata: {e}")
        return {'has_video': True, 'has_audio': True, 'audio_tracks': []}

def generate_hls(file_path, hls_dir, metadata):
    if os.path.exists(os.path.join(hls_dir, 'master.m3u8')):
        return

    os.makedirs(hls_dir, exist_ok=True)

    audio_tracks = metadata['audio_tracks']
    qualities = [
        ('360p', 640, 360, 800000, 28),
        ('480p', 854, 480, 1400000, 26),
        ('720p', 1280, 720, 2800000, 24),
        ('1080p', 1920, 1080, 5000000, 22),
    ]

    cmd = ['ffmpeg', '-hide_banner', '-y', '-i', file_path]

    # Map video for each quality
    for _ in qualities:
        cmd += ['-map', '0:v:0']

    # Map all audio tracks
    for _ in audio_tracks:
        cmd += ['-map', '0:a?']

    # Video codecs and filters
    for i, q in enumerate(qualities):
        cmd += [
            f'-c:v:{i}', 'libx264',
            f'-preset:{i}', 'veryfast',
            f'-crf:{i}', str(q[4]),
            f'-b:v:{i}', str(q[3]),
            f'-vf:{i}', f'scale={q[1]}:{q[2]}:force_original_aspect_ratio=decrease,pad={q[1]}:{q[2]}:(ow-iw)/2:(oh-ih)/2',
            f'-maxrate:{i}', str(q[3]),
            f'-bufsize:{i}', str(q[3] * 2),
        ]

    # Audio codecs
    audio_start = len(qualities)
    for j in range(len(audio_tracks)):
        cmd += [f'-c:a:{audio_start + j}', 'aac', f'-b:a:{audio_start + j}', '128k']

    # HLS settings
    cmd += [
        '-hls_time', '10',
        '-hls_playlist_type', 'vod',
        '-hls_segment_filename', os.path.join(hls_dir, '%v/seg_%03d.ts'),
        '-master_pl_name', 'master.m3u8',
        '-hls_flags', 'independent_segments',
        '-hls_segment_type', 'mpegts',
    ]

    # Var stream map
    vsm = []
    for i, q in enumerate(qualities):
        vsm.append(f'v:{i} a:0 name:{q[0]}')

    for j, track in enumerate(audio_tracks):
        vsm.append(f'a:{j} name:{track["label"]} language:{track["language"]}')

    cmd += ['-var_stream_map', ' '.join(vsm)]
    cmd += [os.path.join(hls_dir, '%v.m3u8')]

    call(cmd)

# ================= REDESIGNED HTML UI =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>THE UPDATED GUYS | {{FILE_NAME}}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://vjs.zencdn.net/8.3.0/video-js.css">
    <script src="https://unpkg.com/lucide@latest"></script>
    {{ADDITIONAL_HEAD}}
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --accent-primary: #6366f1;
            --accent-secondary: #06b6d4;
            --text-primary: #f1f5f9;
            --text-secondary: #cbd5e1;
            --text-muted: #94a3b8;
            --border-light: rgba(255,255,255,0.1);
            --border-dark: rgba(255,255,255,0.05);
            --shadow-sm: 0 4px 6px -1px rgba(0,0,0,0.1);
            --shadow-md: 0 10px 15px -3px rgba(0,0,0,0.1);
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Poppins', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.5;
        }
        .header {
            position: sticky;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-light);
            box-shadow: var(--shadow-sm);
        }
        .header-content {
            max-width: 1280px;
            margin: 0 auto;
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-decoration: none;
        }
        .nav {
            display: flex;
            gap: 1.5rem;
        }
        .nav a {
            color: var(--text-secondary);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s ease;
        }
        .nav a:hover {
            color: var(--accent-primary);
        }
        .mobile-menu {
            display: none;
            background: none;
            border: none;
            color: var(--text-primary);
            cursor: pointer;
        }
        .hero {
            text-align: center;
            padding: 4rem 2rem 2rem;
            background: linear-gradient(to bottom, var(--bg-secondary), transparent);
        }
        .hero-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero-subtitle {
            color: var(--text-muted);
            font-size: 1.25rem;
        }
        .main-container {
            max-width: 1280px;
            margin: 0 auto;
            padding: 2rem;
        }
        .player-section {
            margin-bottom: 3rem;
        }
        .player-wrapper {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: var(--shadow-md);
            background: var(--bg-tertiary);
        }
        .video-container {
            position: relative;
            width: 100%;
            padding-bottom: 56.25%;
        }
        .video-container video {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }
        .info-section {
            margin-top: 2rem;
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 2rem;
            box-shadow: var(--shadow-sm);
        }
        .file-title {
            font-size: 1.75rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        .file-meta {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .meta-tag {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 9999px;
            color: var(--accent-primary);
            font-size: 0.875rem;
            font-weight: 500;
        }
        .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .btn {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-size: 0.875rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
            flex: 1 1 200px;
            max-width: 250px;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: var(--text-primary);
            border: none;
        }
        .btn-primary:hover {
            box-shadow: 0 0 15px rgba(99, 102, 241, 0.4);
            transform: translateY(-2px);
        }
        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border-light);
        }
        .btn-secondary:hover {
            background: rgba(99, 102, 241, 0.1);
            border-color: var(--accent-primary);
            color: var(--accent-primary);
            transform: translateY(-2px);
        }
        .dropdown {
            position: relative;
            flex: 1 1 200px;
            max-width: 250px;
        }
        .dropdown-menu {
            position: absolute;
            top: calc(100% + 0.5rem);
            left: 0;
            width: 100%;
            background: var(--bg-secondary);
            border: 1px solid var(--border-light);
            border-radius: 8px;
            padding: 0.75rem;
            opacity: 0;
            visibility: hidden;
            transform: translateY(-10px);
            transition: all 0.3s ease;
            z-index: 100;
            box-shadow: var(--shadow-sm);
        }
        .dropdown-menu.active {
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }
        .dropdown-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 0.5rem;
        }
        .player-link {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            background: var(--bg-tertiary);
            border-radius: 6px;
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.3s ease;
        }
        .player-link:hover {
            background: rgba(99, 102, 241, 0.1);
            color: var(--accent-primary);
        }
        .player-link img {
            width: 20px;
            height: 20px;
        }
        .explore-section {
            margin-top: 4rem;
        }
        .section-title {
            font-size: 2rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .section-subtitle {
            text-align: center;
            color: var(--text-muted);
            margin-bottom: 2rem;
        }
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }
        .card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: var(--shadow-sm);
            transition: all 0.3s ease;
        }
        .card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-md);
        }
        .card-icon {
            width: 48px;
            height: 48px;
            background: rgba(99, 102, 241, 0.1);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 1rem;
        }
        .card-icon svg {
            color: var(--accent-primary);
            width: 24px;
            height: 24px;
        }
        .card h3 {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
        }
        .card p {
            color: var(--text-secondary);
            font-size: 0.875rem;
            margin-bottom: 1.25rem;
        }
        .card-link {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 1rem;
            background: var(--bg-tertiary);
            border-radius: 6px;
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.3s ease;
        }
        .card-link:hover {
            background: rgba(99, 102, 241, 0.1);
            color: var(--accent-primary);
        }
        .footer {
            text-align: center;
            padding: 3rem 2rem 2rem;
            color: var(--text-muted);
            font-size: 0.875rem;
            border-top: 1px solid var(--border-dark);
            margin-top: 4rem;
        }
        .footer a {
            color: var(--accent-primary);
            text-decoration: none;
            font-weight: 500;
        }
        /* Video.js Styles */
        .video-js {
            font-family: 'Poppins', sans-serif;
        }
        .vjs-big-play-button {
            background: var(--accent-primary) !important;
            border: none !important;
            border-radius: 9999px !important;
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.3) !important;
        }
        .vjs-big-play-button .vjs-icon-placeholder:before {
            color: var(--text-primary) !important;
        }
        .vjs-control-bar {
            background: var(--bg-secondary) !important;
            border-top: 1px solid var(--border-light) !important;
        }
        .vjs-button > .vjs-icon-placeholder:before {
            color: var(--text-primary) !important;
        }
        .vjs-progress-holder {
            background: rgba(255,255,255,0.1) !important;
        }
        .vjs-load-progress {
            background: rgba(255,255,255,0.2) !important;
        }
        .vjs-play-progress {
            background: var(--accent-primary) !important;
        }
        .vjs-time-divider, .vjs-duration, .vjs-current-time {
            color: var(--text-secondary) !important;
        }
        .vjs-menu-content {
            background: var(--bg-secondary) !important;
            border: 1px solid var(--border-light) !important;
            border-radius: 8px !important;
        }
        .vjs-menu li {
            color: var(--text-primary) !important;
        }
        .vjs-menu li.vjs-selected {
            background: rgba(99, 102, 241, 0.1) !important;
            color: var(--accent-primary) !important;
        }
        /* Custom Buttons */
        .vjs-aspect-button, .vjs-theater-button {
            position: relative;
        }
        .vjs-aspect-button .vjs-icon-placeholder:before, .vjs-theater-button .vjs-icon-placeholder:before {
            content: none;
        }
        .vjs-aspect-button i, .vjs-theater-button i {
            stroke: var(--text-primary);
            width: 18px;
            height: 18px;
        }
        .vjs-aspect-button:hover i, .vjs-theater-button:hover i {
            stroke: var(--accent-primary);
        }
        .aspect-dropdown {
            position: absolute;
            bottom: calc(100% + 10px);
            right: 0;
            min-width: 180px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-light);
            border-radius: 8px;
            padding: 0.5rem;
            opacity: 0;
            visibility: hidden;
            transform: translateY(10px);
            transition: all 0.3s ease;
            z-index: 1000;
            box-shadow: var(--shadow-sm);
        }
        .aspect-dropdown.active {
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }
        .aspect-item {
            padding: 0.5rem 0.75rem;
            border-radius: 4px;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .aspect-item:hover {
            background: rgba(99, 102, 241, 0.1);
            color: var(--accent-primary);
        }
        .aspect-item.active {
            background: rgba(99, 102, 241, 0.2);
            color: var(--accent-primary);
        }
        /* Theater Mode */
        .theater-mode .main-container {
            max-width: none;
            padding: 0;
        }
        .theater-mode .player-wrapper {
            border-radius: 0;
            margin: 0;
            box-shadow: none;
        }
        .theater-mode .video-container {
            padding-bottom: 56.25%;
        }
        /* Audio Mode */
        body.is-audio .video-container {
            padding-bottom: 0;
            height: 200px;
        }
        body.is-audio .video-container #waveform {
            width: 100%;
            height: 100%;
        }
        /* Animations */
        .fade-in {
            animation: fadeIn 0.5s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        ::-webkit-scrollbar-thumb {
            background: var(--bg-tertiary);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-primary);
        }
        html {
            scroll-behavior: smooth;
            scroll-padding-top: 70px;
        }
        /* Media Queries */
        @media (max-width: 768px) {
            .header-content {
                padding: 1rem;
            }
            .nav {
                display: none;
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: var(--bg-secondary);
                flex-direction: column;
                padding: 1rem;
                gap: 1rem;
                border-bottom: 1px solid var(--border-light);
                z-index: 999;
                animation: slideDown 0.3s ease-out;
            }
            .nav.active {
                display: flex;
            }
            @keyframes slideDown {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .mobile-menu {
                display: block;
            }
            .hero {
                padding: 3rem 1rem 1rem;
            }
            .hero-title {
                font-size: 2rem;
            }
            .hero-subtitle {
                font-size: 1rem;
            }
            .main-container {
                padding: 1rem;
            }
            .info-section {
                padding: 1.5rem;
            }
            .file-title {
                font-size: 1.5rem;
            }
            .actions {
                flex-direction: column;
            }
            .btn, .dropdown {
                flex: 1 1 auto;
                max-width: none;
            }
            .dropdown-menu {
                position: static;
                transform: none;
                opacity: 1;
                visibility: visible;
                display: none;
            }
            .dropdown-menu.active {
                display: block;
            }
            .cards-grid {
                grid-template-columns: 1fr;
            }
            .explore-section {
                margin-top: 3rem;
            }
        }
    </style>
</head>
<body {{BODY_CLASS}}>
    <header class="header">
        <div class="header-content">
            <a href="https://t.me/THEUPDATEDGUYS" class="logo">THE UPDATED GUYS</a>
            <nav class="nav">
                <a href="#player-section">Stream</a>
                <a href="#explore-section">Explore</a>
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

    <section class="hero">
        <h1 class="hero-title">Stream Effortlessly</h1>
        <p class="hero-subtitle">Anytime, Anywhere with Premium Quality</p>
    </section>

    <main class="main-container">
        <section id="player-section" class="player-section fade-in">
            <div class="player-wrapper">
                <div class="video-container">
                    {{ADDITIONAL_HTML}}
                    {{PLAYER_ELEMENT}}
                </div>
            </div>
        </section>

        <section class="info-section fade-in">
            <h1 class="file-title">{{FILE_NAME}}</h1>
            <div class="file-meta">
                <span class="meta-tag">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    Now {{PLAY_STATUS}}
                </span>
            </div>
            <div class="actions">
                <button class="btn btn-primary" onclick="blazeDownload()">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    Download Original
                </button>
                <button class="btn btn-secondary" onclick="vlc_player()">
                    <img src="https://i.postimg.cc/15TQ4y7B/vlc.png" alt="VLC">
                    VLC Player
                </button>
                <button class="btn btn-secondary" onclick="mx_player()">
                    <img src="https://i.postimg.cc/sx4Msv4T/mx.png" alt="MX">
                    MX Player
                </button>
                <div class="dropdown">
                    <button class="btn btn-secondary" onclick="toggleDropdown(this)">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="1"></circle>
                            <circle cx="19" cy="12" r="1"></circle>
                            <circle cx="5" cy="12" r="1"></circle>
                        </svg>
                        More Players
                    </button>
                    <div class="dropdown-menu" id="players-dropdown">
                        <div class="dropdown-grid">
                            <a href="#" class="player-link" onclick="playit_player(); event.preventDefault();">
                                <img src="https://i.postimg.cc/RVGWYJFF/playit.png" alt="PLAYit">
                                PLAYit
                            </a>
                            <a href="#" class="player-link" onclick="km_player(); event.preventDefault();">
                                <img src="https://i.postimg.cc/wT9tFQ9Z/km.png" alt="KM">
                                KMPlayer
                            </a>
                            <a href="#" class="player-link" onclick="s_player(); event.preventDefault();">
                                <img src="https://i.postimg.cc/XYJr6NGg/s.png" alt="S">
                                S Player
                            </a>
                            <a href="#" class="player-link" onclick="hd_player(); event.preventDefault();">
                                <img src="https://i.postimg.cc/rFT43LNh/hd.png" alt="HD">
                                HD Player
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <section id="explore-section" class="explore-section fade-in">
            <h2 class="section-title">Explore Our Universe</h2>
            <p class="section-subtitle">Discover channels and bots for enhanced experience</p>
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
                    <p>Get exclusive content and real-time updates from our premium channels.</p>
                    <a href="https://t.me/THEUPDATEDGUYS" class="card-link">
                        The Updated Guys
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                            <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                    </a>
                </div>
                <div class="card">
                    <div class="card-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        </svg>
                    </div>
                    <h3>Our Bots</h3>
                    <p>Intelligent bots for seamless streaming and automation.</p>
                    <a href="https://t.me/THEUPDATEDGUYS" class="card-link">
                        Titanium Engine
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                            <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                    </a>
                </div>
            </div>
        </section>
    </main>

    <footer class="footer">
        <p>&copy; 2026 <a href="https://t.me/THEUPDATEDGUYS">THE UPDATED GUYS</a>. All Rights Reserved.</p>
    </footer>

    <script src="https://vjs.zencdn.net/8.3.0/video.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    {{ADDITIONAL_SCRIPT_SRC}}

    <script>
        let originalAspect = '56.25%';
        function initPlayer() {
            const playerEl = document.getElementById('player');
            if (!playerEl) return;

            const player = videojs('player', {
                controls: true,
                autoplay: false,
                preload: 'auto',
                fluid: false,
                aspectRatio: '16:9',
            });

            const src = '{{STREAM_URL}}';
            const type = '{{MIME_TYPE}}';

            if (Hls.isSupported() && type === 'application/x-mpegURL') {
                const hls = new Hls();
                hls.loadSource(src);
                hls.attachMedia(playerEl);
                hls.on(Hls.Events.MANIFEST_PARSED, function() {
                    // Audio Tracks
                    const audioTracks = hls.audioTracks;
                    if (audioTracks.length > 1) {
                        const AudioButton = videojs.getComponent('Button');
                        class CustomAudioButton extends AudioButton {
                            constructor(player, options) {
                                super(player, options);
                                this.addClass('vjs-audio-button');
                                this.controlText('Audio Tracks');
                                this.el().innerHTML += '<i data-lucide="languages"></i>';
                            }
                            handleClick() {
                                document.querySelector('.audio-dropdown')?.classList.toggle('active');
                            }
                        }
                        videojs.registerComponent('CustomAudioButton', CustomAudioButton);
                        player.controlBar.addChild('CustomAudioButton', {}, player.controlBar.children().length - 3);

                        const audioDropdown = document.createElement('div');
                        audioDropdown.className = 'audio-dropdown aspect-dropdown';
                        player.el().appendChild(audioDropdown);

                        audioTracks.forEach((track, index) => {
                            const item = document.createElement('div');
                            item.className = 'aspect-item';
                            item.textContent = track.name || track.lang || `Track ${index + 1}`;
                            if (hls.audioTrack === index) item.classList.add('active');
                            item.addEventListener('click', () => {
                                hls.audioTrack = index;
                                audioDropdown.querySelector('.active')?.classList.remove('active');
                                item.classList.add('active');
                                audioDropdown.classList.remove('active');
                            });
                            audioDropdown.appendChild(item);
                        });
                    }

                    // Quality Levels
                    const levels = hls.levels;
                    if (levels.length > 1) {
                        player.qualityLevels().on('addqualitylevel', function(event) {
                            const qualityLevel = event.qualityLevel;
                            qualityLevel.enabled = true;
                        });
                    }
                });
            } else {
                player.src({src: src, type: type});
            }

            player.on('loadedmetadata', function() {
                originalAspect = (player.videoHeight() / player.videoWidth() * 100) + '%';
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
                    document.querySelector('.aspect-dropdown')?.classList.toggle('active');
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

            // Aspect Logic
            const aspectDropdown = document.querySelector('.aspect-dropdown');
            if (aspectDropdown) {
                aspectDropdown.classList.add('aspect-dropdown');
                player.el().appendChild(aspectDropdown);
            }
            document.querySelectorAll('.aspect-item').forEach(item => {
                item.addEventListener('click', () => {
                    const aspect = item.dataset.aspect;
                    const container = document.querySelector('.video-container');
                    const videoEl = playerEl;
                    let padding = '56.25%';
                    let objectFit = 'contain';
                    switch (aspect) {
                        case 'original':
                            padding = originalAspect;
                            break;
                        case '16:9':
                            padding = '56.25%';
                            break;
                        case '4:3':
                            padding = '75%';
                            break;
                        case 'fill':
                            padding = originalAspect;
                            objectFit = 'fill';
                            break;
                        case 'cover':
                            padding = originalAspect;
                            objectFit = 'cover';
                            break;
                    }
                    container.style.paddingBottom = padding;
                    videoEl.style.objectFit = objectFit;
                    document.querySelector('.aspect-item.active')?.classList.remove('active');
                    item.classList.add('active');
                    aspectDropdown?.classList.remove('active');
                });
            });

            lucide.createIcons();
            {{ADDITIONAL_INIT_SCRIPT}}
        }

        function toggleDropdown(button) {
            const menu = button.nextElementSibling;
            menu.classList.toggle('active');
        }

        function blazeDownload() {
            const a = document.createElement('a');
            a.href = '{{DL_URL}}';
            a.download = '{{FILE_NAME}}';
            a.click();
        }

        function vlc_player() {
            const url = '{{STREAM_URL}}';
            const stripped = url.replace(/^https?:\/\//, '');
            window.location.href = `vlc://${stripped}`;
            setTimeout(() => {
                window.location.href = `intent:${url}#Intent;action=android.intent.action.VIEW;type=video/*;package=org.videolan.vlc;end`;
            }, 500);
        }

        function mx_player() {
            window.location.href = `intent:{{STREAM_URL}}#Intent;action=android.intent.action.VIEW;type=video/*;package=com.mxtech.videoplayer.ad;end`;
        }

        function playit_player() {
            window.location.href = `playit://playerv2/video?url={{STREAM_URL}}`;
        }

        function km_player() {
            window.location.href = `intent:{{STREAM_URL}}#Intent;action=android.intent.action.VIEW;type=video/*;package=com.kmplayer;end`;
        }

        function s_player() {
            window.location.href = `intent:{{STREAM_URL}}#Intent;action=com.young.simple.player.playback_online;package=com.young.simple.player;end`;
        }

        function hd_player() {
            window.location.href = `intent:{{STREAM_URL}}#Intent;action=android.intent.action.VIEW;type=video/*;package=uplayer.video.player;end`;
        }

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.dropdown .btn')) {
                document.querySelectorAll('.dropdown-menu.active').forEach(menu => menu.classList.remove('active'));
            }
            if (!e.target.closest('.vjs-aspect-button')) {
                document.querySelector('.aspect-dropdown')?.classList.remove('active');
            }
            if (!e.target.closest('.vjs-audio-button')) {
                document.querySelector('.audio-dropdown')?.classList.remove('active');
            }
        });

        document.querySelector('.mobile-menu')?.addEventListener('click', () => {
            document.querySelector('.nav').classList.toggle('active');
        });

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initPlayer);
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
    file_path = link_data.get('file_path')  # Assuming db has file_path
    domain = get_domain(request)
    dl_url = f"{domain}/dl/{hash_id}"
    
    metadata = get_metadata(file_path)
    has_video = metadata['has_video']
    ext = file_name.split('.')[-1].lower()
    
    if has_video:
        hls_dir = f'tmp/hls/{hash_id}'
        stream_url = f"{domain}/hls/{hash_id}/master.m3u8"
        mime_type = 'application/x-mpegURL'
        player_element = '<video id="player" class="video-js vjs-big-play-centered" playsinline preload="auto"></video>'
        additional_head = ''
        additional_html = '<div class="aspect-dropdown"><div class="aspect-item" data-aspect="original">Original</div><div class="aspect-item" data-aspect="16:9">16:9</div><div class="aspect-item" data-aspect="4:3">4:3</div><div class="aspect-item" data-aspect="fill">Fill</div><div class="aspect-item" data-aspect="cover">Cover</div></div>'
        additional_script_src = ''
        additional_init_script = ''
        body_class = ''
        play_status = 'Streaming'
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, generate_hls, file_path, hls_dir, metadata)
    else:
        stream_url = f"{domain}/stream/{hash_id}"
        mime_type = f'audio/{ext}' if ext in ['mp3', 'wav', 'ogg'] else 'application/octet-stream'
        player_element = '<audio id="player" class="video-js" playsinline preload="auto"></audio>'
        additional_head = ''
        additional_html = '<div id="waveform"></div>'
        additional_script_src = '<script src="https://unpkg.com/wavesurfer.js@latest/dist/wavesurfer.min.js"></script>'
        additional_init_script = """
            const waveSurfer = WaveSurfer.create({
                container: '#waveform',
                waveColor: 'var(--accent-primary)',
                progressColor: 'var(--accent-secondary)',
                cursorColor: 'var(--text-primary)',
                height: 128,
                barWidth: 3,
                barRadius: 3,
                responsive: true,
                normalize: true
            });
            waveSurfer.load('{{STREAM_URL}}');
            waveSurfer.on('ready', () => {
                player.on('play', () => waveSurfer.play());
                player.on('pause', () => waveSurfer.pause());
            });
        """
        body_class = 'class="is-audio"'
        play_status = 'Playing'

    html = HTML_TEMPLATE.replace('{{FILE_NAME}}', file_name) \
                        .replace('{{STREAM_URL}}', stream_url) \
                        .replace('{{DL_URL}}', dl_url) \
                        .replace('{{MIME_TYPE}}', mime_type) \
                        .replace('{{ADDITIONAL_HEAD}}', additional_head) \
                        .replace('{{ADDITIONAL_HTML}}', additional_html) \
                        .replace('{{PLAYER_ELEMENT}}', player_element) \
                        .replace('{{ADDITIONAL_SCRIPT_SRC}}', additional_script_src) \
                        .replace('{{ADDITIONAL_INIT_SCRIPT}}', additional_init_script) \
                        .replace('{{BODY_CLASS}}', body_class) \
                        .replace('{{PLAY_STATUS}}', play_status)

    return web.Response(text=html, content_type='text/html')

# HLS Serve
@routes.get('/hls/{hash_id}/{path:.*}')
async def hls_serve(request):
    hash_id = request.match_info['hash_id']
    path = request.match_info['path']
    hls_dir = f'tmp/hls/{hash_id}'
    file_path = os.path.join(hls_dir, path)

    if not os.path.exists(file_path):
        return web.Response(status=404)

    headers = {}
    if file_path.endswith('.m3u8'):
        headers['Content-Type'] = 'application/vnd.apple.mpegurl'
    elif file_path.endswith('.ts'):
        headers['Content-Type'] = 'video/mp2t'

    return web.FileResponse(file_path, headers=headers)

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
