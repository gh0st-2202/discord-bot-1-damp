import discord
from discord import app_commands
import time
import asyncio
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

def add_balance_local(discord_id, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE players SET balance = balance + ? WHERE discord_id = ?", (amount, discord_id))
    conn.commit()
    conn.close()

# Importar desde el módulo wordless principal
from cog.juegos.wordless import evaluate_guess, REWARD_1ST, REWARD_2ND, REWARD_BASE

def setup_command(wordless_group, cog):
    """Configura el comando intento en el grupo wordless"""
    
    @wordless_group.command(name="intento", description="Envía un intento en tu partida de Wordless")
    @app_commands.describe(palabra="La palabra de 5 letras que quieres intentar")
    async def intento(interaction: discord.Interaction, palabra: str):
        # Buscar la partida por canal
        game = None
        for user_id, active_game in cog.games.items():
            if active_game.channel.id == interaction.channel.id:
                game = active_game
                break

        if not game:
            await interaction.response.send_message(
                "❌ Este no es un canal de Wordless activo. Usa `/wordless` para empezar una partida.",
                ephemeral=True
            )
            return

        # Verificar que el usuario es el dueño de la partida
        if interaction.user.id != game.user_id:
            await interaction.response.send_message(
                "❌ Esta no es tu partida de Wordless.",
                ephemeral=True
            )
            return

        # Validar la palabra
        palabra = palabra.lower().strip()
        if len(palabra) != 5:
            await interaction.response.send_message(
                "❌ La palabra debe tener exactamente 5 letras.",
                ephemeral=True
            )
            return
        
        if not palabra.isalpha():
            await interaction.response.send_message(
                "❌ La palabra solo debe contener letras (sin números ni símbolos).",
                ephemeral=True
            )
            return

        # Procesar el intento
        game.attempts += 1
        result = evaluate_guess(palabra, game.secret)
        game.guesses.append((palabra, result))

        # Crear embed con el progreso
        embed = discord.Embed(
            title=f"🎯 Intento {game.attempts}/{game.max_attempts}",
            color=discord.Color.blue()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        # Mostrar todos los intentos
        board_text = ""
        for i, (guess_word, guess_result) in enumerate(game.guesses, 1):
            board_text += f"**{i}.** {guess_word.upper()} → {guess_result}\n"
        
        embed.add_field(name="Tus Intentos", value=board_text or "Sin intentos aún", inline=False)
        
        elapsed_time = int(time.time() - game.start_time)
        embed.set_footer(text=f"Tiempo transcurrido: {elapsed_time} segundos")

        await interaction.response.send_message(embed=embed)

        # Verificar si ganó
        if palabra == game.secret:
            # Calcular recompensa
            if game.attempts == 1:
                reward = REWARD_1ST
            elif game.attempts == 2:
                reward = REWARD_2ND
            else:
                reward = REWARD_BASE
            
            # Dar recompensa
            add_balance_local(str(game.user_id), reward)
            player_data = get_player_local(str(game.user_id), interaction.user.name)
            new_balance = player_data[2]

            # Embed de victoria
            win_embed = discord.Embed(
                title="🎉 ¡FELICIDADES! ¡HAS GANADO!",
                description=f"Has adivinado la palabra correcta: **{game.secret.upper()}**",
                color=discord.Color.gold()
            )
            win_embed.add_field(name="Intentos usados", value=f"{game.attempts}", inline=True)
            win_embed.add_field(name="Recompensa", value=f"{reward:,} monedas", inline=True)
            win_embed.add_field(name="Nuevo saldo", value=f"{new_balance:,} monedas", inline=True)
            win_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            await interaction.channel.send(embed=win_embed)
            await cog.end_game(interaction.guild, game.user_id, "win", reward)
            return

        # Verificar si perdió
        if game.attempts >= game.max_attempts:
            lose_embed = discord.Embed(
                title="💀 GAME OVER",
                description="Te has quedado sin intentos.",
                color=discord.Color.red()
            )
            lose_embed.add_field(name="Palabra correcta", value=f"**{game.secret.upper()}**", inline=False)
            lose_embed.add_field(name="Intentos usados", value=f"{game.attempts}", inline=True)
            lose_embed.add_field(name="Recompensa", value="0 monedas", inline=True)
            
            await interaction.channel.send(embed=lose_embed)
            await cog.end_game(interaction.guild, game.user_id, "lose")
