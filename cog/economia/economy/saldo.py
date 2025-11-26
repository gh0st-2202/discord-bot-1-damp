import discord
from discord import app_commands
from typing import Optional
import sqlite3

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

def setup_command(economy_group, cog):
    """Configura el comando saldo en el grupo economy con parámetro opcional"""
    
    @economy_group.command(name="saldo", description="Muestra tu saldo o el de otro usuario")
    @app_commands.describe(usuario="Usuario cuyo saldo quieres ver (opcional)")
    async def saldo(interaction: discord.Interaction, usuario: Optional[discord.User] = None):
        # Determinar el usuario objetivo
        target_user = usuario if usuario else interaction.user
        is_self = target_user.id == interaction.user.id
        
        player = get_player_local(str(target_user.id), target_user.name)
        
        # Crear embed según si es propio o de otro usuario
        if is_self:
            embed = discord.Embed(
                title="💰 Tu Estado de Cuenta",
                color=discord.Color.gold()
            )
            embed.add_field(name="👤 Usuario", value=interaction.user.mention, inline=True)
        else:
            embed = discord.Embed(
                title=f"💰 Saldo de {target_user.display_name}",
                color=discord.Color.blue()
            )
            embed.add_field(name="👤 Usuario", value=target_user.mention, inline=True)
            embed.add_field(name="🔍 Consultado por", value=interaction.user.mention, inline=True)
        
        # Información financiera
        embed.add_field(name="💵 Saldo", value=f"**{player[2]:,}** monedas", inline=True)
        
        # Estadísticas adicionales
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Obtener ranking del usuario
        c.execute("SELECT COUNT(*) FROM players WHERE balance > ?", (player[2],))
        rank = c.fetchone()[0] + 1
        c.execute("SELECT COUNT(*) FROM players")
        total_players = c.fetchone()[0]
        
        embed.add_field(
            name="🏆 Ranking", 
            value=f"**#{rank}** de {total_players} jugadores", 
            inline=True
        )
        
        # Calcular porcentaje del total de riqueza
        c.execute("SELECT SUM(balance) FROM players")
        total_wealth = c.fetchone()[0] or 1
        wealth_percentage = (player[2] / total_wealth) * 100
        
        embed.add_field(
            name="📊 Riqueza Global", 
            value=f"**{wealth_percentage:.2f}%** del total", 
            inline=True
        )
        
        conn.close()
        
        # Footer y thumbnail
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        if is_self:
            embed.set_footer(text="Usa /economy transferir para enviar dinero a otros")
        else:
            embed.set_footer(text=f"Información financiera de {target_user.display_name}")
        
        # Enviar embed (ephemeral si es propio, público si es de otro)
        await interaction.response.send_message(embed=embed, ephemeral=is_self)
