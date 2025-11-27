import discord
from discord import app_commands
from typing import Optional
import sqlite3
import datetime

# Funciones de base de datos locales
DB_FILE = "players.db"
INITIAL_BALANCE = 500

def get_player_local(discord_id, username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
    player = c.fetchone()
    if not player:
        c.execute("INSERT INTO players (discord_id, username, balance, daily_streak, last_daily) VALUES (?, ?, ?, ?, ?)",
                  (discord_id, username, INITIAL_BALANCE, 0, None))
        conn.commit()
        c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
        player = c.fetchone()
    conn.close()
    return player

def claim_daily_reward(discord_id, username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Obtener datos actuales del jugador
    player = get_player_local(discord_id, username)
    current_balance = player[2]
    current_streak = player[3] if len(player) > 3 else 0
    last_daily = player[4] if len(player) > 4 else None
    
    now = datetime.datetime.now()
    
    # Verificar si ya reclamó hoy
    if last_daily:
        last_daily_date = datetime.datetime.fromisoformat(last_daily)
        if last_daily_date.date() == now.date():
            conn.close()
            return None, None, None, "already_claimed"
    
    # Calcular nueva racha
    new_streak = 1
    if last_daily:
        last_daily_date = datetime.datetime.fromisoformat(last_daily)
        days_diff = (now.date() - last_daily_date.date()).days
        
        if days_diff == 1:
            new_streak = current_streak + 1
        elif days_diff > 1:
            new_streak = 1  # Se rompió la racha
    
    # Calcular recompensa (base + bono por racha)
    base_reward = 100
    streak_bonus = min(new_streak * 10, 200)  # Máximo 200 de bono
    total_reward = base_reward + streak_bonus
    
    # Bonus especial cada 7 días
    special_bonus = 0
    if new_streak % 7 == 0:
        special_bonus = 150
    
    final_reward = total_reward + special_bonus
    
    # Actualizar jugador
    new_balance = current_balance + final_reward
    c.execute("""
        UPDATE players 
        SET balance = ?, daily_streak = ?, last_daily = ?
        WHERE discord_id = ?
    """, (new_balance, new_streak, now.isoformat(), discord_id))
    
    conn.commit()
    conn.close()
    
    return final_reward, new_streak, special_bonus, "success"

def setup_command(economy_group, cog):
    """Configura el comando diario en el grupo economy"""
    
    @economy_group.command(name="diario", description="Reclama tu recompensa diaria")
    async def diario(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        username = interaction.user.name
        
        reward, new_streak, special_bonus, status = claim_daily_reward(user_id, username)
        
        if status == "already_claimed":
            # Obtener la hora del próximo daily
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT last_daily FROM players WHERE discord_id = ?", (user_id,))
            last_daily = c.fetchone()[0]
            conn.close()
            
            last_time = datetime.datetime.fromisoformat(last_daily)
            next_daily = last_time + datetime.timedelta(days=1)
            next_daily_time = next_daily.replace(hour=0, minute=0, second=0, microsecond=0)
            
            time_remaining = next_daily_time - datetime.datetime.now()
            hours_remaining = time_remaining.seconds // 3600
            minutes_remaining = (time_remaining.seconds % 3600) // 60
            
            embed = discord.Embed(
                title="⏰ Recompensa Diaria Ya Reclamada",
                color=discord.Color.orange(),
                description=f"Ya reclamaste tu recompensa diaria hoy.\n**Próxima recompensa disponible en:** {hours_remaining}h {minutes_remaining}m"
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
        
        # Mostrar detalles del cálculo
        reward_details = f"• Base: 100 monedas\n• Bono por racha: +{min(new_streak * 10, 200)} monedas"
        if special_bonus > 0:
            reward_details += f"\n• 🎉 Bonus especial ({new_streak} días): +{special_bonus} monedas"
        
        embed.add_field(
            name="📊 Desglose",
            value=reward_details,
            inline=False
        )
        
        # Mensaje especial para rachas altas
        if new_streak >= 7:
            embed.add_field(
                name="🌟 Logro Alcanzado",
                value=f"¡Llevas {new_streak} días consecutivos! Sigue así.",
                inline=False
            )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Vuelve mañana para mantener tu racha y obtener más recompensas!")
        
        await interaction.response.send_message(embed=embed)

