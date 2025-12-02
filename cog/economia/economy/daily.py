import discord
from discord import app_commands
from typing import Optional
import datetime
import sys
import os

# Agregar el directorio padre al path para importar desde economy.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar desde el módulo principal
from economy import get_player, update_player

# Configuración
INITIAL_BALANCE = 500

async def claim_daily_reward(discord_id, username):
    """Reclama la recompensa diaria usando Supabase"""
    try:
        # Obtener jugador
        player = await get_player(discord_id, username)
        if not player:
            return None, None, None, "error"
        
        current_balance = player["balance"]
        current_streak = player.get("daily_streak", 0)
        last_daily = player.get("last_daily")
        
        now = datetime.datetime.now()
        today = now.date()
        
        # Verificar si ya reclamó hoy
        if last_daily:
            last_daily_date = datetime.datetime.fromisoformat(last_daily).date()
            if last_daily_date == today:
                return None, None, None, "already_claimed"
        
        # Calcular nueva racha
        new_streak = 1
        if last_daily:
            last_daily_date = datetime.datetime.fromisoformat(last_daily).date()
            days_diff = (today - last_daily_date).days
            
            if days_diff == 1:
                new_streak = current_streak + 1
            elif days_diff > 1:
                new_streak = 1
        
        # Calcular recompensa
        base_reward = 100
        streak_bonus = min(new_streak * 10, 200)
        total_reward = base_reward + streak_bonus
        
        # Bonus especial cada 7 días
        special_bonus = 0
        if new_streak % 7 == 0:
            special_bonus = 150
        
        final_reward = total_reward + special_bonus
        
        # Actualizar jugador en Supabase
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
    """Configura el comando diario en el grupo economy"""
    
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
        
        # Crear embed de recompensa exitosa
        embed = discord.Embed(
            title="🎁 ¡Recompensa Diaria Reclamada!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="💰 Recompensa",
            value=f"**+{reward} monedas**",
            inline=True
        )
        
        embed.add_field(
            name="🔥 Racha Actual",
            value=f"**{new_streak} días**",
            inline=True
        )
        
        reward_details = f"• Base: 100 monedas\n• Bono por racha: +{min(new_streak * 10, 200)} monedas"
        if special_bonus > 0:
            reward_details += f"\n• 🎉 Bonus especial ({new_streak} días): +{special_bonus} monedas"
        
        embed.add_field(
            name="📊 Desglose",
            value=reward_details,
            inline=False
        )
        
        if new_streak >= 7:
            embed.add_field(
                name="🌟 Logro Alcanzado",
                value=f"¡Llevas {new_streak} días consecutivos! Sigue así.",
                inline=False
            )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Vuelve mañana para mantener tu racha y obtener más recompensas!")
        
        await interaction.response.send_message(embed=embed)
