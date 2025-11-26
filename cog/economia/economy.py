import discord
from discord.ext import commands
from discord import app_commands
import os
import importlib
import sys
import random
import sqlite3
import asyncio
import time

# Grupo de comandos de economía
economy_group = app_commands.Group(
    name="economy", 
    description="Comandos de economía y gestión de dinero",
    default_permissions=None
)

# Funciones de base de datos locales
DB_FILE = "players.db"
INITIAL_BALANCE = 500

def get_player_local(discord_id, username):
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

def update_balance_local(discord_id, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE players SET balance = balance + ? WHERE discord_id = ?", (amount, discord_id))
    conn.commit()
    conn.close()

def get_leaderboard_local():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, balance FROM players ORDER BY balance DESC")
    data = c.fetchall()
    conn.close()
    return data

# Función global para actualizar leaderboard
async def update_global_leaderboard(bot):
    CHANNEL_LEADERBOARD_ID = 1430215076769435800
    channel = bot.get_channel(CHANNEL_LEADERBOARD_ID)
    if not channel:
        print("❌ Canal de leaderboard no encontrado")
        return
    
    try:
        leaderboard = get_leaderboard_local()
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

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loaded_commands = []

    async def load_economy_commands(self):
        """Carga automáticamente todos los comandos de la carpeta economy"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        economy_commands_path = os.path.join(current_dir, "economy")
        
        if not os.path.exists(economy_commands_path):
            print("❌ No se encuentra la carpeta economy")
            return

        if economy_commands_path not in sys.path:
            sys.path.append(economy_commands_path)

        for filename in os.listdir(economy_commands_path):
            if filename.endswith(".py") and filename not in ["__init__.py", "economy.py"]:
                module_name = filename[:-3]
                try:
                    # Importar usando importlib con ruta absoluta
                    spec = importlib.util.spec_from_file_location(
                        module_name, 
                        os.path.join(economy_commands_path, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'setup_command'):
                        module.setup_command(economy_group, self)
                        self.loaded_commands.append(module_name)
                        print(f"✅ Comando economy cargado: {module_name}")
                    else:
                        print(f"⚠️  Módulo {module_name} no tiene función setup_command")
                        
                except Exception as e:
                    print(f"❌ Error al cargar {filename}: {e}")

    async def cog_load(self):
        await self.load_economy_commands()

async def setup(bot):
    bot.tree.add_command(economy_group)
    economy_cog = EconomyCog(bot)
    await bot.add_cog(economy_cog)
