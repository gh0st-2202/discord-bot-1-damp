import discord
from discord import app_commands
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

def setup_command(economy_group, cog):
    """Configura el comando transferir en el grupo economy"""
    
    @economy_group.command(name="transferir", description="Transfiere dinero a otro jugador.")
    @app_commands.describe(destinatario="Usuario al que quieres enviar dinero", cantidad="Cantidad a transferir")
    async def transferir(interaction: discord.Interaction, destinatario: discord.User, cantidad: int):
        if cantidad <= 0:
            await interaction.response.send_message("❌ La cantidad debe ser positiva.", ephemeral=True)
            return
    
        remitente_id = str(interaction.user.id)
        destinatario_id = str(destinatario.id)
        remitente = get_player_local(remitente_id, interaction.user.name)
        get_player_local(destinatario_id, destinatario.name)
    
        if remitente[2] < cantidad:
            await interaction.response.send_message("💸 No tienes suficiente dinero para esta transferencia.", ephemeral=True)
            return
    
        update_balance_local(remitente_id, -cantidad)
        update_balance_local(destinatario_id, cantidad)
        
        embed = discord.Embed(
            title="✅ Transferencia Exitosa",
            color=discord.Color.green()
        )
        embed.add_field(name="De", value=interaction.user.mention, inline=True)
        embed.add_field(name="Para", value=destinatario.mention, inline=True)
        embed.add_field(name="Cantidad", value=f"**{cantidad:,}** monedas", inline=True)
    
        await interaction.response.send_message(embed=embed)
        await update_global_leaderboard(cog.bot)
