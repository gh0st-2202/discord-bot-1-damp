import discord
from discord import app_commands
import sqlite3

# Función de base de datos local
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

def setup_command(blackjack_group, cog):
    """Configura el comando unirse en el grupo blackjack"""
    
    @blackjack_group.command(name="unirse", description="Únete a la partida de Blackjack actual.")
    @app_commands.describe(apuesta="Cantidad a apostar")
    async def unirse(interaction: discord.Interaction, apuesta: int):
        if cog.current_bet_min == 0:
            await interaction.response.send_message("❌ No hay ninguna partida activa. Usa `/blackjack play` para iniciar una.", ephemeral=True)
            return
    
        if interaction.user in cog.player_bets:
            await interaction.response.send_message("❌ Ya estás en la partida.", ephemeral=True)
            return
    
        if apuesta < cog.current_bet_min:
            await interaction.response.send_message(f"❌ La apuesta mínima es de {cog.current_bet_min:,} monedas.", ephemeral=True)
            return
    
        player_data = get_player_local(str(interaction.user.id), interaction.user.name)
        if player_data[2] < apuesta:
            await interaction.response.send_message(f"❌ No tienes suficiente dinero. Tu saldo: {player_data[2]:,} monedas.", ephemeral=True)
            return
    
        cog.player_bets[interaction.user] = apuesta
    
        embed = discord.Embed(
            title="✅ Jugador Unido",
            description=f"{interaction.user.mention} se ha unido a la partida",
            color=discord.Color.green()
        )
        embed.add_field(name="Apuesta", value=f"**{apuesta:,}** monedas", inline=True)
        embed.add_field(name="Saldo Restante", value=f"**{player_data[2] - apuesta:,}** monedas", inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
    
        await interaction.response.send_message(embed=embed)
