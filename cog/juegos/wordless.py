import discord
from discord import app_commands
from discord.ext import commands
import os
import importlib
import sys
import random
import time
import sqlite3

# Grupo de comandos de wordless
wordless_group = app_commands.Group(
    name="wordless", 
    description="Comandos para jugar al Wordless (Wordle)",
    default_permissions=None
)

# Constantes
TEMP_CHANNEL_PREFIX = "wordless-"
REWARD_1ST = 1000
REWARD_2ND = 500
REWARD_BASE = 100

# Lista de palabras para el juego
WORD_LIST = [
    "casa", "perro", "gato", "arbol", "flor", "sol", "luna", "agua", "fuego", "tierra",
    "aire", "viento", "nube", "lluv", "nieve", "mar", "rio", "monte", "valle", "campo",
    "bosque", "playa", "isla", "pueblo", "ciudad", "calle", "coche", "moto", "bici", "avion",
    "barco", "tren", "bus", "camion", "puente", "edificio", "casa", "puerta", "ventana", "techo",
    "suelo", "pared", "mesa", "silla", "cama", "sofa", "armario", "cocina", "baño", "comedor",
    "salon", "dormir", "comer", "beber", "jugar", "trabajar", "estudiar", "leer", "escribir", "pintar",
    "musica", "cancion", "baile", "teatro", "cine", "libro", "revista", "periodico", "radio", "tv",
    "ordenador", "movil", "tablet", "internet", "red", "web", "email", "chat", "video", "foto",
    "amigo", "familia", "padre", "madre", "hijo", "hija", "hermano", "hermana", "abuelo", "abuela",
    "tio", "tia", "primo", "prima", "vecino", "companero", "jefe", "empleado", "cliente", "proveedor",
    "tiempo", "futuro", "pasado", "presente", "ayer", "hoy", "manana", "semana", "mes", "ano",
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
    "noviembre", "diciembre", "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo",
    "primavera", "verano", "otono", "invierno", "calor", "frio", "fresco", "templado", "humedo", "seco",
    "norte", "sur", "este", "oeste", "derecha", "izquierda", "arriba", "abajo", "delante", "detras",
    "centro", "medio", "borde", "esquina", "linea", "curva", "recta", "circulo", "cuadrado", "triangulo",
    "rojo", "azul", "verde", "amarillo", "naranja", "rosa", "morado", "blanco", "negro", "gris",
    "claro", "oscuro", "brillante", "opaco", "transparente", "sólido", "liquido", "gas", "fuego", "tierra",
    "agua", "aire", "fuego", "metal", "madera", "piedra", "cristal", "plastico", "papel", "tela",
    "comida", "agua", "pan", "leche", "carne", "pescado", "fruta", "verdura", "arroz", "pasta",
    "sopa", "ensalada", "postre", "dulce", "salado", "amargo", "acido", "picante", "suave", "fuerte",
    "rapido", "lento", "grande", "pequeno", "alto", "bajo", "largo", "corto", "ancho", "estrecho",
    "pesado", "ligero", "duro", "blando", "suave", "áspero", "liso", "rugoso", "caliente", "frio",
    "nuevo", "viejo", "joven", "antiguo", "moderno", "actual", "futuro", "pasado", "presente", "eterno"
]

# Funciones de utilidad para wordless
def choose_word():
    return random.choice(WORD_LIST)

def evaluate_guess(guess, secret):
    result = []
    for i, letter in enumerate(guess):
        if letter == secret[i]:
            result.append("🟩")
        elif letter in secret:
            result.append("🟨")
        else:
            result.append("⬛")
    return "".join(result)

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

# Clases del juego
class WordlessGame:
    def __init__(self, user_id, channel, secret_word):
        self.user_id = user_id
        self.channel = channel
        self.secret = secret_word
        self.attempts = 0
        self.max_attempts = 6
        self.guesses = []  # Lista de tuplas (palabra, resultado)
        self.start_time = time.time()

class ForfeitButton(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id

    @discord.ui.button(label="Rendirse", style=discord.ButtonStyle.danger, custom_id="forfeit")
    async def forfeit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.games.get(self.user_id)
        if game:
            await interaction.response.send_message(f"Te has rendido. La palabra era: **{game.secret.upper()}**")
            await self.cog.end_game(interaction.guild, self.user_id, "forfeit")
        else:
            await interaction.response.send_message("No hay partida activa.", ephemeral=True)

class WordlessCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loaded_commands = []
        self.games = {}

    async def load_wordless_commands(self):
        """Carga automáticamente todos los comandos de la carpeta wordless"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        wordless_commands_path = os.path.join(current_dir, "wordless")
        
        if not os.path.exists(wordless_commands_path):
            print("❌ No se encuentra la carpeta wordless")
            return

        if wordless_commands_path not in sys.path:
            sys.path.append(wordless_commands_path)

        for filename in os.listdir(wordless_commands_path):
            if filename.endswith(".py") and filename not in ["__init__.py", "wordless.py"]:
                module_name = filename[:-3]
                try:
                    # Importar usando importlib con ruta absoluta
                    spec = importlib.util.spec_from_file_location(
                        module_name, 
                        os.path.join(wordless_commands_path, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'setup_command'):
                        module.setup_command(wordless_group, self)
                        self.loaded_commands.append(module_name)
                        print(f"✅ Comando wordless cargado: {module_name}")
                    else:
                        print(f"⚠️  Módulo {module_name} no tiene función setup_command")
                        
                except Exception as e:
                    print(f"❌ Error al cargar {filename}: {e}")

    async def end_game(self, guild, user_id, outcome, reward=0):
        """Termina una partida de Wordless"""
        if user_id in self.games:
            game = self.games[user_id]
            try:
                # Eliminar canal
                await game.channel.delete(reason="Partida de Wordless terminada")
            except Exception as e:
                print(f"❌ Error al eliminar canal: {e}")
            # Eliminar juego
            del self.games[user_id]

    async def cog_load(self):
        await self.load_wordless_commands()

async def setup(bot):
    bot.tree.add_command(wordless_group)
    wordless_cog = WordlessCog(bot)
    await bot.add_cog(wordless_cog)
