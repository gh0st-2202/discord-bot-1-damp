import discord
from discord import app_commands
import os
import time
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Inicializar cliente de Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Configuración
INITIAL_BALANCE = 500

# Funciones de base de datos locales
async def get_player(discord_id, username):
    """Obtiene o crea un jugador en Supabase"""
    try:
        response = supabase.table("players").select("*").eq("discord_id", discord_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
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
        response = supabase.table("players").select("balance").eq("discord_id", discord_id).execute()
        
        if response.data and len(response.data) > 0:
            current_balance = response.data[0]["balance"]
            new_balance = current_balance + amount
            
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

async def update_global_leaderboard(bot):
    """Actualiza el leaderboard global en el canal especificado"""
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

def setup_command(sudo_group):
    """Configura el comando give directamente en el grupo sudo"""
    
    @sudo_group.command(name="give", description="Da o quita dinero a un jugador (solo admin)")
    @app_commands.describe(usuario="Usuario al que darle dinero", cantidad="Cantidad (positiva o negativa)")
    async def give(interaction: discord.Interaction, usuario: discord.User, cantidad: int):
        # Nota: Los permisos ya están manejados por el grupo sudo
        
        # Crear/obtener jugador
        await get_player(str(usuario.id), usuario.name)
        
        # Actualizar balance
        nuevo_saldo = await update_balance(str(usuario.id), cantidad)
        
        embed = discord.Embed(
            title="💰 Modificación de Saldo - Administrador",
            color=discord.Color.green() if cantidad >= 0 else discord.Color.orange()
        )
        embed.add_field(name="👨‍💼 Administrador", value=interaction.user.mention, inline=True)
        embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
        embed.add_field(name="💵 Cantidad", value=f"**{cantidad:,}** monedas", inline=True)
        embed.add_field(name="💳 Nuevo Saldo", value=f"**{nuevo_saldo:,}** monedas", inline=False)
        
        # Información adicional para el administrador
        cambio = "añadido" if cantidad >= 0 else "restado"
        embed.add_field(
            name="📊 Resumen", 
            value=f"Se han {cambio} **{abs(cantidad):,}** monedas al usuario {usuario.mention}",
            inline=False
        )
        
        embed.set_thumbnail(url=usuario.display_avatar.url)
        embed.set_footer(text=f"Operación realizada por {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
        await update_global_leaderboard(interaction.client)
