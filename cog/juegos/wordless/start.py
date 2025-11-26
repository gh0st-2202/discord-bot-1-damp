import discord
from discord import app_commands
import random
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

# Importar desde el módulo wordless principal
from cog.juegos.wordless import choose_word, TEMP_CHANNEL_PREFIX, REWARD_1ST, REWARD_2ND, REWARD_BASE, WordlessGame, ForfeitButton

def setup_command(wordless_group, cog):
    """Configura el comando wordless en el grupo wordless"""
    
    @wordless_group.command(name="start", description="Inicia una partida privada de Wordless (Wordle)")
    async def start(interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # Verificar si ya tiene una partida activa
        if user_id in cog.games:
            await interaction.response.send_message(
                "❌ Ya tienes una partida activa. Termina la actual antes de empezar una nueva.", 
                ephemeral=True
            )
            return

        # Crear canal privado
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        # Crear nombre seguro para el canal
        safe_name = interaction.user.name.lower().replace(" ", "-")[:20]
        channel_name = f"{TEMP_CHANNEL_PREFIX}{safe_name}-{random.randint(1000, 9999)}"

        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                reason="Canal temporal para partida de Wordless"
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error al crear el canal: {e}", 
                ephemeral=True
            )
            return

        # Inicializar juego
        secret_word = choose_word()
        game = WordlessGame(user_id, channel, secret_word)
        cog.games[user_id] = game

        # Enviar mensaje de bienvenida al canal privado
        view = ForfeitButton(cog, user_id)
        embed = discord.Embed(
            title="🎯 Wordless - Partida Privada",
            description=(
                f"Hola {interaction.user.mention}! Bienvenido a tu partida privada de Wordless.\n\n"
                f"**Instrucciones:**\n"
                f"• Adivina la palabra de **5 letras**\n"
                f"• Usa `/wordless intento <palabra>` para enviar tus intentos\n"
                f"• Tienes **{game.max_attempts}** intentos máximo\n"
                f"• Recompensas: 1er intento = {REWARD_1ST}, 2do = {REWARD_2ND}, otros = {REWARD_BASE} monedas\n\n"
                f"¡Buena suerte! 🍀"
            ),
            color=discord.Color.purple()
        )
        await channel.send(embed=embed, view=view)

        # Responder al usuario
        await interaction.response.send_message(
            f"✅ ¡Partida creada! Ve a {channel.mention} para jugar.", 
            ephemeral=True
        )
