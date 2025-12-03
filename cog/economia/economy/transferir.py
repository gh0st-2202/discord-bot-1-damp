import discord
from discord import app_commands
import time
import os
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
CHANNEL_LEADERBOARD_ID = int(os.getenv("CHANNEL_LEADERBOARD_ID"))

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

def setup_command(economy_group, cog):
    @economy_group.command(name="transferir", description="Transfiere dinero a otro jugador.")
    @app_commands.describe(destinatario="Usuario al que quieres enviar dinero", cantidad="Cantidad a transferir")
    async def transferir(interaction: discord.Interaction, destinatario: discord.User, cantidad: int):
        if cantidad <= 0:
            await interaction.response.send_message("❌ La cantidad debe ser positiva.", ephemeral=True)
            return
        
        remitente_id = str(interaction.user.id)
        destinatario_id = str(destinatario.id)
        
        try:
            # Obtener jugador remitente
            remitente = await get_player(remitente_id, interaction.user.name)
            if not remitente:
                await interaction.response.send_message("❌ No se pudo encontrar tu información.", ephemeral=True)
                return
            
            # Verificar si el remitente tiene suficiente dinero
            if remitente["balance"] < cantidad:
                await interaction.response.send_message("💸 No tienes suficiente dinero para esta transferencia.", ephemeral=True)
                return
            
            # Asegurar que el destinatario existe
            await get_player(destinatario_id, destinatario.name)
            
            # Realizar transferencia
            await update_balance(remitente_id, -cantidad)
            await update_balance(destinatario_id, cantidad)
            
            embed = discord.Embed(
                title="✅ Transferencia Exitosa",
                color=discord.Color.green()
            )
            embed.add_field(name="De", value=interaction.user.mention, inline=True)
            embed.add_field(name="Para", value=destinatario.mention, inline=True)
            embed.add_field(name="Cantidad", value=f"**{cantidad:,}** monedas", inline=True)
            
            await interaction.response.send_message(embed=embed)
            
            # Actualizar leaderboard
            await update_global_leaderboard(cog.bot)
            
        except Exception as e:
            print(f"Error en transferir: {e}")
            await interaction.response.send_message("❌ Ha ocurrido un error al procesar la transferencia.", ephemeral=True)
