import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import sqlite3
import os
import time
from dotenv import load_dotenv

# ------------------------- CONFIGURACIÓN DEL BOT ---------------------------
load_dotenv()
TOKEN = 'MTQyOTk2NDg3ODQ5MTE1NjQ5MA.Gr-o88.SRIGy3cSzDFx98rOBUAjhO7v6DkI3KB5Nizl-I'
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

# -------------------- CARGA BASE DATOS (DEFINICIONES) ----------------------
def setup_database():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tabla de jugadores
    c.execute("""
    CREATE TABLE IF NOT EXISTS players (
        discord_id TEXT PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 500
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Base de datos verificada o creada correctamente.")

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
