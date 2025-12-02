import discord
from discord.ext import commands
from discord import app_commands
import os
import importlib
import sys
import random
import asyncio
import time
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Inicializar cliente de Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Grupo de comandos de economía
economy_group = app_commands.Group(
    name="economy", 
    description="Comandos de economía y gestión de dinero",
    default_permissions=None
)

# Configuración inicial
INITIAL_BALANCE = 500

# Funciones de base de datos con Supabase
async def get_player(discord_id, username):
    """Obtiene o crea un jugador en Supabase"""
    try:
        # Buscar jugador existente
        response = supabase.table("players").select("*").eq("discord_id", discord_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            # Crear nuevo jugador
            new_player = {
                "discord_id": discord_id,
                "username": username,
                "balance": INITIAL_BALANCE,
                "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            response = supabase.table("players").insert(new_player).execute()
            return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error en get_player: {e}")
        return None

async def update_balance(discord_id, amount):
    """Actualiza el balance de un jugador en Supabase"""
    try:
        # Primero obtener el balance actual
        response = supabase.table("players").select("balance").eq("discord_id", discord_id).execute()
        
        if response.data and len(response.data) > 0:
            current_balance = response.data[0]["balance"]
            new_balance = current_balance + amount
            
            # Actualizar el balance
            supabase.table("players").update({"balance": new_balance}).eq("discord_id", discord_id).execute()
            return new_balance
        return None
    except Exception as e:
        print(f"Error en update_balance: {e}")
        return None

async def get_leaderboard(limit=10):
    """Obtiene el leaderboard desde Supabase"""
    try:
        response = supabase.table("players").select("username, balance").order("balance", desc=True).limit(limit).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error en get_leaderboard: {e}")
        return []

async def get_player_by_discord_id(discord_id):
    """Obtiene un jugador específico por discord_id"""
    try:
        response = supabase.table("players").select("*").eq("discord_id", discord_id).execute()
        return response.data[0] if response.data and len(response.data) > 0 else None
    except Exception as e:
        print(f"Error en get_player_by_discord_id: {e}")
        return None

async def set_balance(discord_id, amount):
    """Establece un balance específico para un jugador"""
    try:
        supabase.table("players").update({"balance": amount}).eq("discord_id", discord_id).execute()
        return True
    except Exception as e:
        print(f"Error en set_balance: {e}")
        return False

# Función global para actualizar leaderboard
async def update_global_leaderboard(bot):
    CHANNEL_LEADERBOARD_ID = 1430215076769435800
    channel = bot.get_channel(CHANNEL_LEADERBOARD_ID)
    if not channel:
        print("❌ Canal de leaderboard no encontrado")
        return
    
    try:
        leaderboard = await get_leaderboard(10)
        await channel.purge()
        
        embed = discord.Embed(title="🏆 TABLA DE LÍDERES GLOBAL", color=discord.Color.gold())
        
        for i, player in enumerate(leaderboard[:10], start=1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            embed.add_field(
                name=f"{medal} {player['username']}", 
                value=f"```{player['balance']:,} monedas```", 
                inline=False
            )
        
        embed.set_footer(text="Actualizado automáticamente")
        await channel.send(embed=embed)
        print("✅ Leaderboard global actualizado")
        
    except Exception as e:
        print(f"❌ Error actualizando leaderboard: {e}")
        
# Exportar funciones para que otros módulos puedan importarlas
__all__ = ['get_player', 'update_balance', 'get_leaderboard', 'update_player', 'get_player_by_discord_id', 'set_balance', 'supabase']

# Nota: Asegúrate de que estas funciones existan en tu economy.py
# Si no tienes update_player, agrégalo:
async def update_player(discord_id, data):
    """Actualiza múltiples campos de un jugador en Supabase"""
    try:
        supabase.table("players").update(data).eq("discord_id", discord_id).execute()
        return True
    except Exception as e:
        print(f"Error en update_player: {e}")
        return False

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
