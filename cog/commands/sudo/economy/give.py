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

def setup_command(sudo_group):
    """Configura el comando give directamente en el grupo sudo"""
    
    @sudo_group.command(name="give", description="Da o quita dinero a un jugador (solo admin)")
    @app_commands.describe(usuario="Usuario al que darle dinero", cantidad="Cantidad (positiva o negativa)")
    async def give(interaction: discord.Interaction, usuario: discord.User, cantidad: int):
        # Nota: Los permisos ya están manejados por el grupo sudo
        
        get_player_local(str(usuario.id), usuario.name)
        update_balance_local(str(usuario.id), cantidad)
        player = get_player_local(str(usuario.id), usuario.name)
        nuevo_saldo = player[2]
    
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
