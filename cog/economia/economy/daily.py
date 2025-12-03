import discord
from discord import app_commands
import datetime
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

async def update_player(discord_id, data):
    """Actualiza múltiples campos de un jugador en Supabase"""
    try:
        supabase.table("players").update(data).eq("discord_id", discord_id).execute()
        return True
    except Exception as e:
        print(f"Error en update_player: {e}")
        return False

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

async def claim_daily_reward(discord_id, username):
    """Reclama la recompensa diaria usando Supabase"""
    try:
        player = await get_player(discord_id, username)
        if not player:
            return None, None, None, "error"
        
        current_balance = player["balance"]
        current_streak = player.get("daily_streak", 0)
        last_daily = player.get("last_daily")
        
        now = datetime.datetime.now()
        today = now.date()
        
        if last_daily:
            last_daily_date = datetime.datetime.fromisoformat(last_daily).date()
            if last_daily_date == today:
                return None, None, None, "already_claimed"
        
        new_streak = 1
        if last_daily:
            last_daily_date = datetime.datetime.fromisoformat(last_daily).date()
            days_diff = (today - last_daily_date).days
            
            if days_diff == 1:
                new_streak = current_streak + 1
            elif days_diff > 1:
                new_streak = 1
        
        base_reward = 100
        streak_bonus = min(new_streak * 10, 200)
        total_reward = base_reward + streak_bonus
        
        special_bonus = 0
        if new_streak % 7 == 0:
            special_bonus = 150
        
        final_reward = total_reward + special_bonus
        
        new_balance = current_balance + final_reward
        await update_player(discord_id, {
            "balance": new_balance,
            "daily_streak": new_streak,
            "last_daily": now.isoformat()
        })
        
        return final_reward, new_streak, special_bonus, "success"
        
    except Exception as e:
        print(f"Error en claim_daily_reward: {e}")
        return None, None, None, "error"

def setup_command(economy_group, cog):
    @economy_group.command(name="diario", description="Reclama tu recompensa diaria")
    async def diario(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        username = interaction.user.name
        
        reward, new_streak, special_bonus, status = await claim_daily_reward(user_id, username)
        
        if status == "already_claimed":
            now = datetime.datetime.now()
            tomorrow = now.date() + datetime.timedelta(days=1)
            midnight = datetime.datetime.combine(tomorrow, datetime.time.min)
            
            time_remaining = midnight - now
            hours_remaining = time_remaining.seconds // 3600
            minutes_remaining = (time_remaining.seconds % 3600) // 60
            
            embed = discord.Embed(
                title="⏰ Recompensa Diaria Ya Reclamada",
                color=discord.Color.orange(),
                description=f"Ya reclamaste tu recompensa diaria hoy.\n**Próxima recompensa disponible en:** {hours_remaining}h {minutes_remaining}m"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if status == "error":
            embed = discord.Embed(
                title="❌ Error",
                description="Ha ocurrido un error al procesar tu recompensa diaria.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🎁 ¡Recompensa Diaria Reclamada!",
            color=discord.Color.green()
        )
        
        embed.add_field(name="💰 Recompensa", value=f"**+{reward} monedas**", inline=True)
        embed.add_field(name="🔥 Racha Actual", value=f"**{new_streak} días**", inline=True)
        
        reward_details = f"• Base: 100 monedas\n• Bono por racha: +{min(new_streak * 10, 200)} monedas"
        if special_bonus > 0:
            reward_details += f"\n• 🎉 Bonus especial ({new_streak} días): +{special_bonus} monedas"
        
        embed.add_field(name="📊 Desglose", value=reward_details, inline=False)
        
        if new_streak >= 7:
            embed.add_field(
                name="🌟 Logro Alcanzado",
                value=f"¡Llevas {new_streak} días consecutivos! Sigue así.",
                inline=False
            )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Vuelve mañana para mantener tu racha y obtener más recompensas!")
        
        await interaction.response.send_message(embed=embed)
        
        # Actualizar leaderboard global
        try:
            await update_global_leaderboard(interaction.client)
            print(f"✅ Leaderboard actualizado después de recompensa diaria de {username}")
        except Exception as e:
            print(f"❌ Error actualizando leaderboard después de daily: {e}")
