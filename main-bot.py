import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import sqlite3
import os
import time
from dotenv import load_dotenv
from aiohttp import web
import urllib.parse

# ------------------------- CONFIGURACIÓN DEL BOT ---------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DB_FILE = "players.db"
INITIAL_BALANCE = 500

# IDs de canales
CHANNEL_BET_ID = 1430216318933794927
CHANNEL_TROPHY_ID = 1430215324111736953
CHANNEL_LEADERBOARD_ID = 1430215076769435800

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
# ---------------------------------------------------------------------------

# ----------------------- SERVIDOR WEB CON EXPLORADOR DE ARCHIVOS -----------
def get_file_tree(startpath=".", max_depth=3):
    """Genera el árbol de archivos y directorios"""
    tree = []
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        if level > max_depth:
            continue
            
        # Excluir algunas carpetas del bot por seguridad
        exclude_dirs = ['__pycache__', '.git', 'node_modules']
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        indent = '  ' * level
        tree.append(f'{indent}📁 {os.path.basename(root)}/')
        subindent = '  ' * (level + 1)
        
        for file in files:
            # Excluir algunos archivos por seguridad
            if file.endswith(('.pyc', '.env', '.db')):
                continue
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            tree.append(f'{subindent}📄 {file} ({file_size} bytes)')
    
    return '\n'.join(tree)

def generate_file_list_html(base_path="."):
    """Genera HTML con la lista de archivos navegable"""
    # Normalizar y asegurar que no salgamos del directorio seguro
    safe_base = os.path.abspath(base_path)
    
    html = []
    html.append('''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Explorador de Archivos</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #1e1e1e;
                color: #ffffff;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }
            .file-explorer {
                background: #2d2d2d;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }
            .breadcrumb {
                background: #3d3d3d;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 15px;
                font-size: 14px;
            }
            .file-list {
                list-style: none;
                padding: 0;
            }
            .file-item {
                padding: 10px;
                margin: 5px 0;
                background: #3d3d3d;
                border-radius: 5px;
                display: flex;
                align-items: center;
                transition: background 0.3s;
            }
            .file-item:hover {
                background: #4d4d4d;
            }
            .file-icon {
                margin-right: 10px;
                font-size: 18px;
            }
            .file-name {
                flex-grow: 1;
            }
            .file-size {
                color: #888;
                font-size: 12px;
                margin-left: 10px;
            }
            .download-btn {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                cursor: pointer;
                text-decoration: none;
                font-size: 12px;
            }
            .download-btn:hover {
                background: #45a049;
            }
            .folder-link {
                color: #64b5f6;
                text-decoration: none;
            }
            .folder-link:hover {
                text-decoration: underline;
            }
            .current-path {
                word-break: break-all;
                background: #2d2d2d;
                padding: 10px;
                border-radius: 5px;
                font-family: monospace;
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🖥️ Explorador de Archivos del Bot</h1>
            <p>Navega por los archivos y directorios disponibles</p>
        </div>
    ''')
    
    # Breadcrumb navigation
    html.append('<div class="breadcrumb">')
    html.append('<a href="/" class="folder-link">🏠 Inicio</a>')
    html.append('</div>')
    
    # Current path
    html.append(f'<div class="current-path">📍 Ruta actual: {safe_base}</div>')
    
    # File list
    html.append('<div class="file-explorer">')
    html.append('<h3>📂 Contenido:</h3>')
    html.append('<ul class="file-list">')
    
    try:
        # List directories first
        items = []
        for item in os.listdir(safe_base):
            item_path = os.path.join(safe_base, item)
            
            # Excluir carpetas y archivos sensibles
            if item.startswith(('.', '__')) or item in ['__pycache__', '.git', 'node_modules']:
                continue
                
            items.append((item, item_path, os.path.isdir(item_path)))
        
        # Sort: directories first, then files
        items.sort(key=lambda x: (not x[2], x[0].lower()))
        
        for item, item_path, is_dir in items:
            if is_dir:
                # Es un directorio
                html.append(f'''
                <li class="file-item">
                    <span class="file-icon">📁</span>
                    <span class="file-name">
                        <a href="/browse?path={urllib.parse.quote(item_path)}" class="folder-link">{item}/</a>
                    </span>
                    <span class="file-size">[DIRECTORIO]</span>
                </li>
                ''')
            else:
                # Es un archivo
                file_size = os.path.getsize(item_path)
                size_str = f"{file_size} bytes"
                if file_size > 1024:
                    size_str = f"{file_size/1024:.1f} KB"
                if file_size > 1024*1024:
                    size_str = f"{file_size/(1024*1024):.1f} MB"
                
                html.append(f'''
                <li class="file-item">
                    <span class="file-icon">📄</span>
                    <span class="file-name">{item}</span>
                    <span class="file-size">{size_str}</span>
                    <a href="/download?file={urllib.parse.quote(item_path)}" class="download-btn">📥 Descargar</a>
                </li>
                ''')
                
    except PermissionError:
        html.append('<li class="file-item">❌ Permiso denegado para acceder a este directorio</li>')
    except Exception as e:
        html.append(f'<li class="file-item">❌ Error: {str(e)}</li>')
    
    html.append('</ul>')
    html.append('</div>')
    
    # Tree view
    html.append('<div class="file-explorer">')
    html.append('<h3>🌳 Vista de árbol (primeros 3 niveles):</h3>')
    html.append('<pre style="background: #1e1e1e; padding: 15px; border-radius: 5px; overflow-x: auto;">')
    html.append(get_file_tree(safe_base))
    html.append('</pre>')
    html.append('</div>')
    
    html.append('</body></html>')
    
    return ''.join(html)

async def handle_file_explorer(request):
    """Manejador principal del explorador de archivos"""
    return web.Response(
        text=generate_file_list_html(),
        content_type='text/html'
    )

async def handle_browse(request):
    """Manejador para navegar por directorios"""
    path = request.query.get('path', '')
    if not path:
        return web.HTTPFound('/')
    
    try:
        # Verificar que el path es seguro
        safe_path = os.path.abspath(path)
        if not os.path.exists(safe_path) or not os.path.isdir(safe_path):
            return web.Response(text="Directorio no encontrado", status=404)
            
        return web.Response(
            text=generate_file_list_html(safe_path),
            content_type='text/html'
        )
    except Exception as e:
        return web.Response(text=f"Error: {str(e)}", status=500)

async def handle_download(request):
    """Manejador para descargar archivos"""
    file_path = request.query.get('file', '')
    if not file_path:
        return web.Response(text="Archivo no especificado", status=400)
    
    try:
        # Verificar que el path es seguro y el archivo existe
        safe_path = os.path.abspath(file_path)
        if not os.path.exists(safe_path) or not os.path.isfile(safe_path):
            return web.Response(text="Archivo no encontrado", status=404)
        
        # Verificar que no es un archivo sensible
        sensitive_extensions = ['.env']
        if any(safe_path.endswith(ext) for ext in sensitive_extensions):
            return web.Response(text="No se puede descargar este tipo de archivo", status=403)
        
        return web.FileResponse(safe_path)
    except Exception as e:
        return web.Response(text=f"Error: {str(e)}", status=500)

async def start_web_server():
    """Inicia el servidor web con el explorador de archivos"""
    app = web.Application()
    
    # Rutas
    app.router.add_get('/', handle_file_explorer)
    app.router.add_get('/browse', handle_browse)
    app.router.add_get('/download', handle_download)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    print("🌐 Servidor web iniciado en puerto 8080")
    print("📁 Explorador de archivos disponible en: http://0.0.0.0:8080")
    return runner
# ---------------------------------------------------------------------------

# -------------------- CARGA BASE DATOS (DEFINICIONES) ----------------------
def setup_database():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tabla de jugadores (mejorada con sistema de recompensas diarias)
    c.execute("""
    CREATE TABLE IF NOT EXISTS players (
        discord_id TEXT PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 500,
        daily_streak INTEGER DEFAULT 0,
        last_daily TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Base de datos mejorada creada correctamente.")
setup_database()
# ---------------------------------------------------------------------------

# --------------------- FUNCIONES DE BASE DE DATOS --------------------------
def get_player(discord_id, username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
    player = c.fetchone()
    if not player:
        c.execute("INSERT INTO players (discord_id, username, balance) VALUES (?, ?, ?)",
                  (discord_id, username, INITIAL_BALANCE))
        conn.commit()
        c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
        player = c.fetchone()
    conn.close()
    return player

def update_balance(discord_id, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE players SET balance = balance + ? WHERE discord_id = ?", (amount, discord_id))
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, balance FROM players ORDER BY balance DESC")
    data = c.fetchall()
    conn.close()
    return data
# ---------------------------------------------------------------------------

# --------------------- FUNCIONES GLOBALES --------------------------------
async def update_global_leaderboard():
    """Función global para actualizar el leaderboard"""
    channel = bot.get_channel(CHANNEL_LEADERBOARD_ID)
    if not channel:
        print("❌ Canal de leaderboard no encontrado")
        return
    
    try:
        leaderboard = get_leaderboard()
        await channel.purge()
        
        embed = discord.Embed(title="🏆 TABLA DE LÍDERES GLOBAL", color=discord.Color.gold())
        
        for i, (name, balance) in enumerate(leaderboard[:10], start=1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            embed.add_field(
                name=f"{medal} {name}", 
                value=f"```{balance:,} monedas```", 
                inline=False
            )
        
        embed.set_footer(text="Actualizado automáticamente")
        await channel.send(embed=embed)
        print("✅ Leaderboard global actualizado")
        
    except Exception as e:
        print(f"❌ Error actualizando leaderboard: {e}")

async def update_global_trophy_wall(winner=None, game_type="Blackjack"):
    """Función global para actualizar el muro de trofeos"""
    channel = bot.get_channel(CHANNEL_TROPHY_ID)
    if not channel:
        return
    
    try:
        await channel.purge()
        
        embed = discord.Embed(
            title="🎊 MURO DE LA FAMA",
            description=f"Últimos ganadores de {game_type}",
            color=discord.Color.green()
        )
        
        if winner:
            if isinstance(winner, list):
                for i, w in enumerate(winner[:5]):
                    embed.add_field(
                        name=f"🏅 {w.display_name}",
                        value=f"Ganó en la última partida de {game_type}",
                        inline=False
                    )
            else:
                embed.add_field(
                    name=f"🏅 {winner.display_name}",
                    value=f"Ganó en la última partida de {game_type}",
                    inline=False
                )
        else:
            embed.description = f"💀 Nadie ha ganado en la última partida de {game_type}"
        
        embed.set_footer(text="Actualizado después de cada partida")
        await channel.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Error actualizando muro de trofeos: {e}")
# ---------------------------------------------------------------------------

# --------------------- CARGA DE COGS (DEFINICIONES) ------------------------
async def load_juegos():
    """Carga todos los cogs de la carpeta cog/juegos"""
    for filename in os.listdir("./cog/juegos"):
        if filename.endswith(".py") and not filename.startswith("_"):
            try:
                await bot.load_extension(f"cog.juegos.{filename[:-3]}")
                print(f"✅ Cog cargado: {filename}")
            except Exception as e:
                print(f"❌ Error al cargar {filename}: {e}")

async def load_ia():
    """Carga todos los cogs de la carpeta cog/ia"""
    for filename in os.listdir("./cog/ia"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cog.ia.{filename[:-3]}")
                print(f"✅ Cog cargado: {filename}")
            except Exception as e:
                print(f"❌ Error al cargar {filename}: {e}")

async def load_economia():
    """Carga todos los cogs de la carpeta cog/economia"""
    for filename in os.listdir("./cog/economia"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cog.economia.{filename[:-3]}")
                print(f"✅ Cog cargado: {filename}")
            except Exception as e:
                print(f"❌ Error al cargar {filename}: {e}")
    
async def load_commands():
    """Carga todos los cogs de la carpeta cog/commands"""
    for filename in os.listdir("./cog/commands"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cog.commands.{filename[:-3]}")
                print(f"✅ Cog cargado: {filename}")
            except Exception as e:
                print(f"❌ Error al cargar {filename}: {e}")
                

async def load_all():
    await load_juegos()
    await load_economia()
    await load_ia()
    await load_commands()
# ---------------------------------------------------------------------------

# ------------------------------ CARGAR BOT ---------------------------------
@bot.event
async def on_ready():
    # Iniciar servidor web
    await start_web_server()
    
    # Cargar extensiones
    await load_all() 
    print(f"🤖 Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"📜 {len(synced)} comandos sincronizados:")
        for cmd in synced:
            print(f"   - /{cmd.name}")
    except Exception as e:
        print(f"❌ Error sincronizando comandos: {e}")
# ---------------------------------------------------------------------------

bot.run(TOKEN)
