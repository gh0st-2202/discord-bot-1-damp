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

# ------------------------- CONFIGURACIÓN DEL BOT ---------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
INITIAL_BALANCE = 500

# Configuración de GitHub
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL")  # URL del repositorio GitHub
GITHUB_BACKUP_DIR = "./github_backup"  # Directorio temporal para git
BACKUP_INTERVAL = 300  # 5 minutos en segundos

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Inicializar cliente de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bot.supabase = supabase  # Hacerlo disponible para otros cogs
# ---------------------------------------------------------------------------

# -------------------- CREACIÓN DE TABLAS EN SUPABASE -----------------------
def setup_supabase_tables():
    """Crea todas las tablas necesarias en Supabase si no existen"""
    print("🔧 Configurando tablas en Supabase...")
    
    try:
        # Verificar conexión primero
        supabase.table("players").select("count", count="exact").limit(1).execute()
        print("✅ Conexión a Supabase establecida")
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
        print("⚠️  Asegúrate de que:")
        print(f"  1. SUPABASE_URL está configurado: {SUPABASE_URL}")
        print(f"  2. SUPABASE_KEY está configurado: {SUPABASE_KEY[:10]}...")
        print("  3. El proyecto Supabase está activo")
        return False
    
    try:
        # Crear tabla players si no existe
        try:
            supabase.table("players").select("*").limit(1).execute()
            print("✅ Tabla 'players' ya existe")
        except Exception:
            print("📦 Creando tabla 'players'...")
            # Ejecutar SQL para crear tabla players
            sql_players = """
            CREATE TABLE IF NOT EXISTS players (
                discord_id TEXT PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 500,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            supabase.rpc('exec_sql', {'sql': sql_players}).execute()
            print("✅ Tabla 'players' creada")
        
        # Crear tabla crypto_wallets si no existe
        try:
            supabase.table("crypto_wallets").select("*").limit(1).execute()
            print("✅ Tabla 'crypto_wallets' ya existe")
        except Exception:
            print("📦 Creando tabla 'crypto_wallets'...")
            sql_crypto_wallets = """
            CREATE TABLE IF NOT EXISTS crypto_wallets (
                discord_id TEXT PRIMARY KEY,
                btc_balance REAL DEFAULT 0,
                eth_balance REAL DEFAULT 0,
                dog_balance REAL DEFAULT 0,
                last_btc_trade TIMESTAMP WITH TIME ZONE,
                last_eth_trade TIMESTAMP WITH TIME ZONE,
                last_dog_trade TIMESTAMP WITH TIME ZONE,
                total_invested REAL DEFAULT 0,
                total_withdrawn REAL DEFAULT 0
            );
            """
            supabase.rpc('exec_sql', {'sql': sql_crypto_wallets}).execute()
            print("✅ Tabla 'crypto_wallets' creada")
        
        # Crear tabla crypto_prices si no existe
        try:
            supabase.table("crypto_prices").select("*").limit(1).execute()
            print("✅ Tabla 'crypto_prices' ya existe")
        except Exception:
            print("📦 Creando tabla 'crypto_prices'...")
            sql_crypto_prices = """
            CREATE TABLE IF NOT EXISTS crypto_prices (
                id BIGSERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                btc_price REAL,
                eth_price REAL,
                dog_price REAL
            );
            """
            supabase.rpc('exec_sql', {'sql': sql_crypto_prices}).execute()
            print("✅ Tabla 'crypto_prices' creada")
        
        # Crear tabla crypto_current_prices si no existe
        try:
            supabase.table("crypto_current_prices").select("*").limit(1).execute()
            print("✅ Tabla 'crypto_current_prices' ya existe")
        except Exception:
            print("📦 Creando tabla 'crypto_current_prices'...")
            sql_current_prices = """
            CREATE TABLE IF NOT EXISTS crypto_current_prices (
                crypto TEXT PRIMARY KEY,
                price REAL,
                last_update TIMESTAMP WITH TIME ZONE
            );
            """
            supabase.rpc('exec_sql', {'sql': sql_current_prices}).execute()
            print("✅ Tabla 'crypto_current_prices' creada")
        
        # Insertar datos iniciales
        insert_initial_data()
        
        print("🎉 Base de datos en Supabase configurada correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas en Supabase: {e}")
        print("⚠️  Posibles soluciones:")
        print("  1. Verifica que tengas permisos para crear tablas")
        print("  2. Crea las tablas manualmente en el dashboard de Supabase")
        print("  3. Verifica la conexión a internet")
        return False

def insert_initial_data():
    """Inserta datos iniciales en las tablas"""
    try:
        # Verificar e insertar precios iniciales
        response = supabase.table("crypto_current_prices").select("*").execute()
        if len(response.data) == 0:
            initial_prices = [
                {"crypto": "BTC", "price": 10000, "last_update": datetime.now().isoformat()},
                {"crypto": "ETH", "price": 3000, "last_update": datetime.now().isoformat()},
                {"crypto": "DOG", "price": 50, "last_update": datetime.now().isoformat()}
            ]
            for price_data in initial_prices:
                try:
                    supabase.table("crypto_current_prices").insert(price_data).execute()
                except:
                    # Si ya existe, actualizar
                    supabase.table("crypto_current_prices").update(price_data).eq("crypto", price_data["crypto"]).execute()
            print("✅ Precios iniciales insertados/actualizados")
        
        # Insertar primer registro histórico
        response = supabase.table("crypto_prices").select("*").execute()
        if len(response.data) == 0:
            supabase.table("crypto_prices").insert({
                "btc_price": 10000,
                "eth_price": 3000,
                "dog_price": 50
            }).execute()
            print("✅ Registro histórico inicial insertado")
            
    except Exception as e:
        print(f"⚠️  Error insertando datos iniciales: {e}")

# Función alternativa si exec_sql no está disponible
def create_tables_alternative():
    """Método alternativo para crear tablas usando la API REST"""
    print("🔄 Usando método alternativo para crear tablas...")
    
    # Esta función intentará crear tablas mediante inserciones/consultas
    # Si fallan, asumimos que las tablas no existen y debemos crearlas manualmente
    
    try:
        # Verificar si podemos acceder a las tablas
        try:
            supabase.table("players").select("count", count="exact").limit(0).execute()
            print("✅ Tabla 'players' accesible")
        except Exception as e:
            print("❌ Tabla 'players' no existe o no es accesible")
            print("   Crea la tabla manualmente con este SQL:")
            print("""
            CREATE TABLE players (
                discord_id TEXT PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 500,
                daily_streak INTEGER DEFAULT 0,
                last_daily TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """)
            return False
            
        # Verificar el resto de tablas de manera similar
        tables = ["crypto_wallets", "crypto_prices", "crypto_current_prices"]
        for table in tables:
            try:
                supabase.table(table).select("count", count="exact").limit(0).execute()
                print(f"✅ Tabla '{table}' accesible")
            except Exception:
                print(f"❌ Tabla '{table}' no existe o no es accesible")
                print(f"   Crea la tabla '{table}' manualmente en el dashboard de Supabase")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
        return False

# Llamar a setup_database al inicio
if not setup_supabase_tables():
    print("🔄 Intentando método alternativo...")
    create_tables_alternative()
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
    print(f"🤖 Bot conectado como {bot.user}")
    
    # Cargar extensiones
    await load_all() 
    
    # Sincronizar comandos
    try:
        synced = await bot.tree.sync()
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

bot.run(TOKEN)
