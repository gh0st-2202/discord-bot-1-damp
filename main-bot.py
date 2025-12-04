import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from dotenv import load_dotenv
import subprocess
import shutil
from datetime import datetime
from supabase import create_client, Client
import postgrest
import time
from flask import Flask, render_template_string
import threading

# ------------------------- CONFIGURACIÓN DEL BOT ---------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
INITIAL_BALANCE = 500

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Inicializar cliente de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bot.supabase = supabase  # Hacerlo disponible para otros cogs

# ------------------------- SERVIDOR WEB FLASK -----------------------------
app = Flask(__name__)

# Variables para el estado del bot
bot_status = {
    "status": "iniciando",
    "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "guild_count": 0,
    "user_count": 0,
    "command_count": 0
}

# Plantilla HTML para la página web
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Estado del Bot Discord</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 800px;
            width: 100%;
            text-align: center;
        }
        
        .header {
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #333;
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header p {
            color: #666;
            font-size: 1.1rem;
        }
        
        .status-card {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            border-left: 5px solid #667eea;
            transition: transform 0.3s ease;
        }
        
        .status-card:hover {
            transform: translateY(-5px);
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
        }
        
        .status-online {
            background-color: #4CAF50;
            box-shadow: 0 0 10px #4CAF50;
        }
        
        .status-offline {
            background-color: #f44336;
        }
        
        .status-starting {
            background-color: #ff9800;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        
        .stat-box {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            border: 1px solid #eaeaea;
        }
        
        .stat-box h3 {
            color: #667eea;
            font-size: 2rem;
            margin-bottom: 5px;
        }
        
        .stat-box p {
            color: #666;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .footer {
            margin-top: 30px;
            color: #888;
            font-size: 0.9rem;
        }
        
        .last-update {
            color: #667eea;
            font-weight: bold;
        }
        
        .uptime {
            background: linear-gradient(45deg, #4CAF50, #8BC34A);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            display: inline-block;
            margin-top: 15px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Bot Discord</h1>
            <p>Sistema de economía y juegos para Discord</p>
        </div>
        
        <div class="status-card">
            <h2>
                <span class="status-indicator {{ 'status-online' if status == 'online' else 'status-starting' if status == 'iniciando' else 'status-offline' }}"></span>
                Estado: 
                {% if status == 'online' %}
                    <span style="color: #4CAF50;">CONECTADO ✅</span>
                {% elif status == 'iniciando' %}
                    <span style="color: #ff9800;">INICIANDO ⚠️</span>
                {% else %}
                    <span style="color: #f44336;">DESCONECTADO ❌</span>
                {% endif %}
            </h2>
            <p>Servidor web funcionando en puerto 8080</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-box">
                <h3>{{ guild_count }}</h3>
                <p>Servidores</p>
            </div>
            <div class="stat-box">
                <h3>{{ user_count }}</h3>
                <p>Usuarios Totales</p>
            </div>
            <div class="stat-box">
                <h3>{{ command_count }}</h3>
                <p>Comandos</p>
            </div>
            <div class="stat-box">
                <h3>{{ start_time.split(' ')[0] }}</h3>
                <p>Fecha de Inicio</p>
            </div>
        </div>
        
        <div class="uptime">
            ⏰ {{ uptime }}
        </div>
        
        <div class="footer">
            <p>Última actualización: <span class="last-update">{{ last_update }}</span></p>
            <p>Bot diseñado para Discord | Sistema de economía con Supabase</p>
        </div>
    </div>
    
    <script>
        // Actualizar la página cada 30 segundos
        setTimeout(function() {
            location.reload();
        }, 30000);
        
        // Mostrar hora actualizada
        function updateTime() {
            const now = new Date();
            document.querySelector('.last-update').textContent = 
                now.toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit'});
        }
        
        // Actualizar cada segundo
        setInterval(updateTime, 1000);
        updateTime();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    # Calcular tiempo de actividad
    start = datetime.strptime(bot_status["start_time"], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    uptime = now - start
    
    # Formatear el tiempo de actividad
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m"
    else:
        uptime_str = f"{minutes}m {seconds}s"
    
    return render_template_string(HTML_TEMPLATE,
        status=bot_status["status"],
        start_time=bot_status["start_time"],
        guild_count=bot_status["guild_count"],
        user_count=bot_status["user_count"],
        command_count=bot_status["command_count"],
        last_update=datetime.now().strftime("%H:%M:%S"),
        uptime=uptime_str
    )

@app.route('/health')
def health():
    return {
        "status": bot_status["status"],
        "timestamp": datetime.now().isoformat(),
        "service": "discord_bot",
        "version": "1.0.0"
    }

@app.route('/api/stats')
def stats():
    return bot_status

def run_web_server():
    """Inicia el servidor web Flask"""
    print(f"🌐 Iniciando servidor web en puerto 8080...")
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

# Iniciar servidor web en un hilo separado
web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()
# ---------------------------------------------------------------------------

# --------------------- FUNCIONES DE BASE DE DATOS --------------------------
def get_player(discord_id, username):
    """Obtiene o crea un jugador en Supabase"""
    try:
        # Intentar obtener el jugador
        response = supabase.table("players")\
            .select("*")\
            .eq("discord_id", str(discord_id))\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            # Crear nuevo jugador
            new_player = {
                "discord_id": str(discord_id),
                "username": username,
                "balance": INITIAL_BALANCE,
                "daily_streak": 0,
                "created_at": datetime.now().isoformat()
            }
            response = supabase.table("players").insert(new_player).execute()
            
            # También crear wallet de criptomonedas si no existe
            try:
                supabase.table("crypto_wallets")\
                    .select("*")\
                    .eq("discord_id", str(discord_id))\
                    .execute()
            except:
                new_wallet = {
                    "discord_id": str(discord_id),
                    "btc_balance": 0,
                    "eth_balance": 0,
                    "dog_balance": 0,
                    "total_invested": 0,
                    "total_withdrawn": 0
                }
                supabase.table("crypto_wallets").insert(new_wallet).execute()
            
            return response.data[0] if response.data else None
            
    except Exception as e:
        print(f"❌ Error en get_player: {e}")
        return None

def update_balance(discord_id, amount):
    """Actualiza el balance de un jugador en Supabase"""
    try:
        # Primero obtener el balance actual
        response = supabase.table("players")\
            .select("balance")\
            .eq("discord_id", str(discord_id))\
            .execute()
        
        if response.data and len(response.data) > 0:
            current_balance = response.data[0]["balance"]
            new_balance = current_balance + amount
            
            # Actualizar balance
            supabase.table("players")\
                .update({"balance": new_balance})\
                .eq("discord_id", str(discord_id))\
                .execute()
            
            return new_balance
        else:
            # Si no existe el jugador, crearlo primero
            from discord.utils import get
            guild = bot.guilds[0] if bot.guilds else None
            member = guild.get_member(int(discord_id)) if guild else None
            username = member.name if member else "Unknown"
            
            get_player(discord_id, username)
            return amount + INITIAL_BALANCE  # Balance inicial + lo ganado
            
    except Exception as e:
        print(f"❌ Error en update_balance: {e}")
        return None

def get_leaderboard():
    """Obtiene el leaderboard desde Supabase"""
    try:
        response = supabase.table("players")\
            .select("username, balance, discord_id")\
            .order("balance", desc=True)\
            .limit(10)\
            .execute()
        
        return response.data
    except Exception as e:
        print(f"❌ Error en get_leaderboard: {e}")
        return []

def get_crypto_wallet(discord_id):
    """Obtiene la wallet de criptomonedas de un usuario"""
    try:
        response = supabase.table("crypto_wallets")\
            .select("*")\
            .eq("discord_id", str(discord_id))\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            # Crear wallet si no existe
            new_wallet = {
                "discord_id": str(discord_id),
                "btc_balance": 0,
                "eth_balance": 0,
                "dog_balance": 0,
                "total_invested": 0,
                "total_withdrawn": 0
            }
            supabase.table("crypto_wallets").insert(new_wallet).execute()
            return new_wallet
    except Exception as e:
        print(f"❌ Error en get_crypto_wallet: {e}")
        return None

# Hacer funciones disponibles globalmente
bot.get_player = get_player
bot.update_balance = update_balance
bot.get_leaderboard = get_leaderboard
bot.get_crypto_wallet = get_crypto_wallet
# ---------------------------------------------------------------------------

# --------------------- CARGA DE COGS ------------------------
async def load_juegos():
    for filename in os.listdir("./cog/juegos"):
        if filename.endswith(".py") and not filename.startswith("_"):
            try:
                await bot.load_extension(f"cog.juegos.{filename[:-3]}")
                print(f"✅ Cog cargado: {filename}")
            except Exception as e:
                print(f"❌ Error al cargar {filename}: {e}")

async def load_ia():
    for filename in os.listdir("./cog/ia"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cog.ia.{filename[:-3]}")
                print(f"✅ Cog cargado: {filename}")
            except Exception as e:
                print(f"❌ Error al cargar {filename}: {e}")

async def load_economia():
    for filename in os.listdir("./cog/economia"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cog.economia.{filename[:-3]}")
                print(f"✅ Cog cargado: {filename}")
            except Exception as e:
                print(f"❌ Error al cargar {filename}: {e}")
    
async def load_commands():
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
    # Actualizar estado del bot
    bot_status["status"] = "online"
    bot_status["guild_count"] = len(bot.guilds)
    bot_status["user_count"] = sum(guild.member_count for guild in bot.guilds)
    
    print(f"🤖 Bot conectado como {bot.user}")
    
    # Cargar extensiones
    await load_all() 
    
    # Sincronizar comandos
    try:
        synced = await bot.tree.sync()
        bot_status["command_count"] = len(synced)
        print(f"📜 {len(synced)} comandos cargados:")
        
        # Mostrar cada comando cargado
        for cmd in synced:
            print(f"  /{cmd.name}")
            
    except Exception as e:
        print(f"❌ Error sincronizando comandos: {e}")
    
    # Iniciar tareas en segundo plan
    await start_background_tasks()

async def start_background_tasks():
    """Inicia tareas en segundo plano"""
    # Ejemplo: Actualizar precios cada hora
    bot.loop.create_task(update_crypto_prices_loop())
    print("✅ Tareas en segundo plano iniciadas")

async def update_crypto_prices_loop():
    """Bucle para actualizar precios de criptomonedas periódicamente"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            # Aquí puedes agregar lógica para actualizar precios
            # Por ahora, solo un placeholder
            await asyncio.sleep(3600)  # Esperar 1 hora
        except Exception as e:
            print(f"❌ Error en update_crypto_prices_loop: {e}")
            await asyncio.sleep(300)  # Esperar 5 minutos si hay error
# ---------------------------------------------------------------------------

# ---------------------- MIGRACIÓN DE DATOS EXISTENTES ----------------------
def migrate_from_sqlite():
    """Migra datos de SQLite a Supabase si existe la base de datos local"""
    sqlite_db = "players.db"
    if os.path.exists(sqlite_db):
        print("🔄 Detectada base de datos SQLite, iniciando migración...")
        try:
            import sqlite3
            conn = sqlite3.connect(sqlite_db)
            cursor = conn.cursor()
            
            # Migrar jugadores
            cursor.execute("SELECT * FROM players")
            players = cursor.fetchall()
            
            for player in players:
                player_data = {
                    "discord_id": player[0],
                    "username": player[1],
                    "balance": player[2],
                    "daily_streak": player[3] if len(player) > 3 else 0,
                    "last_daily": player[4] if len(player) > 4 else None,
                    "created_at": player[5] if len(player) > 5 else datetime.now().isoformat()
                }
                try:
                    # Intentar insertar, si existe actualizar
                    supabase.table("players").upsert(player_data).execute()
                except Exception as e:
                    print(f"⚠️  Error migrando jugador {player[0]}: {e}")
            
            # Migrar wallets de criptomonedas
            try:
                cursor.execute("SELECT * FROM crypto_wallets")
                wallets = cursor.fetchall()
                
                for wallet in wallets:
                    wallet_data = {
                        "discord_id": wallet[0],
                        "btc_balance": wallet[1] if len(wallet) > 1 else 0,
                        "eth_balance": wallet[2] if len(wallet) > 2 else 0,
                        "dog_balance": wallet[3] if len(wallet) > 3 else 0,
                        "last_btc_trade": wallet[4] if len(wallet) > 4 else None,
                        "last_eth_trade": wallet[5] if len(wallet) > 5 else None,
                        "last_dog_trade": wallet[6] if len(wallet) > 6 else None,
                        "total_invested": wallet[7] if len(wallet) > 7 else 0,
                        "total_withdrawn": wallet[8] if len(wallet) > 8 else 0
                    }
                    try:
                        supabase.table("crypto_wallets").upsert(wallet_data).execute()
                    except Exception as e:
                        print(f"⚠️  Error migrando wallet {wallet[0]}: {e}")
            except sqlite3.OperationalError:
                print("ℹ️  Tabla crypto_wallets no existe en SQLite, omitiendo...")
            
            conn.close()
            print("✅ Migración completada")
            
        except Exception as e:
            print(f"❌ Error en migración: {e}")
    else:
        print("ℹ️  No se encontró base de datos SQLite para migrar")

# Ejecutar migración al inicio (opcional, comentar si no se necesita)
migrate_from_sqlite()
# ---------------------------------------------------------------------------

# ------------------------ INICIAR BOT ---------------------------------------
try:
    print("🚀 Iniciando bot y servidor web...")
    bot.run(TOKEN)
except Exception as e:
    bot_status["status"] = "error"
    print(f"❌ Error al iniciar bot: {e}")
