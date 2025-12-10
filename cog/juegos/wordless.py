import discord
from discord import app_commands
from discord.ext import commands
import time
import random
import asyncio
import os
import json
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
TEMP_CHANNEL_PREFIX = "wordless-"
REWARD_1ST = 1000
REWARD_2ND = 500
REWARD_BASE = 100

# Cargar listas de palabras desde archivos JSON
def load_word_lists():
    """Carga las listas de palabras objetivo y permitidas desde archivos JSON"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        # Cargar palabras objetivo
        with open(current_dir + '/wordless/objetivo-5-letras.json', 'r', encoding='utf-8') as f:
            target_words = json.load(f)
        
        # Cargar palabras permitidas
        with open(current_dir + '/wordless/permitidas-5-letras.json', 'r', encoding='utf-8') as f:
            allowed_words = json.load(f)
        
        target_words = [word.lower().strip() for word in target_words]
        allowed_words = [word.lower().strip() for word in allowed_words]
        
        print(f"✅ Cargadas {len(target_words)} palabras objetivo y {len(allowed_words)} palabras permitidas")
        return target_words, allowed_words
    except FileNotFoundError as e:
        print(f"❌ Error: No se encontró el archivo {e.filename}")
        # Listas de respaldo en caso de error
        backup_target = ["casa", "perro", "gato", "mesa", "silla", "arbol", "flor", "libro", "lapiz", "reloj"]
        backup_allowed = backup_target + ["cielo", "tierra", "agua", "fuego", "viento"]
        return backup_target, backup_allowed
    except json.JSONDecodeError as e:
        print(f"❌ Error al parsear JSON: {e}")
        return [], []

# Cargar las listas de palabras al inicio
TARGET_WORDS, ALLOWED_WORDS = load_word_lists()

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

# Funciones del juego Wordless
def choose_word():
    """Elige una palabra objetivo aleatoria de la lista"""
    if not TARGET_WORDS:
        print("⚠️ Lista de palabras objetivo vacía, usando palabra por defecto")
        return "casa"
    return random.choice(TARGET_WORDS).lower()

def evaluate_guess(guess, secret):
    """Evalúa un intento y devuelve el resultado con emojis"""
    length = len(secret)
    result = ["⬛"] * length
    secret_list = list(secret)
    guess_list = list(guess)

    # Primera pasada: verdes (posición exacta)
    for i in range(length):
        if guess_list[i] == secret_list[i]:
            result[i] = "🟩"
            secret_list[i] = None
            guess_list[i] = None

    # Segunda pasada: amarillas (letra correcta pero posición incorrecta)
    for i in range(length):
        if guess_list[i] is not None:
            if guess_list[i] in secret_list:
                result[i] = "🟨"
                # Removemos la primera ocurrencia en secret_list
                j = secret_list.index(guess_list[i])
                secret_list[j] = None

    return "".join(result)

def is_valid_word(word):
    """Verifica si una palabra está en la lista de palabras permitidas"""
    return word.lower() in ALLOWED_WORDS

# Clases del juego
class WordlessGame:
    """Representa una partida de Wordless"""
    def __init__(self, user_id, channel, secret_word):
        self.user_id = user_id
        self.channel = channel
        self.secret = secret_word
        self.attempts = 0
        self.max_attempts = 6
        self.guesses = []  # Lista de tuplas (palabra, resultado)
        self.start_time = time.time()

class ForfeitButton(discord.ui.View):
    """Botón para rendirse en Wordless"""
    def __init__(self, cog, user_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id

    @discord.ui.button(label="Rendirse", style=discord.ButtonStyle.danger, custom_id="forfeit")
    async def forfeit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.games.get(self.user_id)
        if game:
            # Obtener información del jugador
            player_data = await get_player(str(game.user_id), interaction.user.name)
            
            embed = discord.Embed(
                title="🏳️ Te has rendido",
                description=f"La palabra era: **{game.secret.upper()}**",
                color=discord.Color.red()
            )
            embed.add_field(name="Intentos usados", value=f"{game.attempts}", inline=True)
            embed.add_field(name="Tu saldo", value=f"{player_data['balance']:,} monedas", inline=True)
            
            await interaction.response.send_message(embed=embed)
            
            # Terminar el juego
            await asyncio.sleep(3)
            await self.cog.end_game(interaction.guild, self.user_id)
        else:
            await interaction.response.send_message("No hay partida activa.", ephemeral=True)

class WordlessCog(commands.Cog):
    """Cog principal para el juego Wordless"""
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    async def end_game(self, guild, user_id):
        """Termina una partida de Wordless"""
        if user_id in self.games:
            game = self.games[user_id]
            try:
                # Esperar 3 segundos antes de eliminar el canal
                await asyncio.sleep(3)
                await game.channel.delete(reason="Partida de Wordless terminada")
            except Exception as e:
                print(f"❌ Error al eliminar canal: {e}")
            
            # Eliminar juego del diccionario
            del self.games[user_id]

    # Grupo de comandos de Wordless
    wordless = app_commands.Group(name="wordless", description="Comandos para jugar al Wordless (Wordle)")

    @wordless.command(name="crear", description="Inicia una partida privada de Wordless (Wordle)")
    async def crear(self, interaction: discord.Interaction):
        """Comando para iniciar una nueva partida de Wordless"""
        user_id = interaction.user.id
        
        # Verificar si ya tiene una partida activa
        if user_id in self.games:
            await interaction.response.send_message(
                "❌ Ya tienes una partida activa. Termina la actual antes de empezar una nueva.", 
                ephemeral=True
            )
            return

        # Verificar que hay palabras objetivo disponibles
        if not TARGET_WORDS:
            await interaction.response.send_message(
                "❌ Error: No hay palabras objetivo disponibles. Contacta con un administrador.",
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
        self.games[user_id] = game

        print(f"🎯 Nueva partida de Wordless para {interaction.user.name} (ID: {user_id})")
        print(f"🔑 Palabra objetivo: {secret_word}")

        # Enviar mensaje de bienvenida al canal privado
        view = ForfeitButton(self, user_id)
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

    @wordless.command(name="intento", description="Envía un intento en tu partida de Wordless")
    @app_commands.describe(palabra="La palabra de 5 letras que quieres intentar")
    async def intento(self, interaction: discord.Interaction, palabra: str):
        """Comando para enviar un intento en Wordless"""
        # Buscar la partida por canal
        game = None
        for user_id, active_game in self.games.items():
            if active_game.channel.id == interaction.channel.id:
                game = active_game
                break

        if not game:
            await interaction.response.send_message(
                "❌ Este no es un canal de Wordless activo. Usa `/wordless crear` para empezar una partida.",
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
        
        # Verificar que la palabra esté en la lista de palabras permitidas
        if not is_valid_word(palabra):
            await interaction.response.send_message(
                "❌ Esa palabra no existe en español o no es válida para el juego.",
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
            new_balance = await update_balance(str(game.user_id), reward)
            player_data = await get_player(str(game.user_id), interaction.user.name)
            
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
            
            # Actualizar leaderboard
            try:
                await update_global_leaderboard(self.bot)
                print(f"✅ Leaderboard actualizado después de victoria en Wordless de {interaction.user.name}")
            except Exception as e:
                print(f"❌ Error actualizando leaderboard después de Wordless: {e}")
            
            # Terminar el juego
            await asyncio.sleep(3)
            await self.end_game(interaction.guild, game.user_id)
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
            await self.end_game(interaction.guild, game.user_id)

async def setup(bot):
    """Función de setup para cargar el cog"""
    await bot.add_cog(WordlessCog(bot))
