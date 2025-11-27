import discord
from discord import app_commands
from discord.ext import commands
from time import sleep
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
    "abaco", "abajo", "abeja", "abono", "abril", "abrir", "abuso", "acabo", "acaso", "acero", 
    "acido", "actor", "acusa", "adios", "adobo", "agudo", "aguja", "ahogo", "ahora", "alaba", 
    "aldea", "algun", "altar", "amaba", "amada", "amado", "amiga", "amigo", "ancho", "andar", 
    "angel", "animo", "antes", "apoyo", "apuro", "arena", "arbol", "ardor", "atada", "armas", 
    "aroma", "arroz", "asado", "ataca", "atado", "atras", "audio", "autor", "avena", "avisa", 
    "aviso", "ayuda", "ayuno", "anoso", "baila", "baile", "bajar", "balas", "balde", "banco", 
    "banda", "barba", "barca", "barco", "barra", "barro", "basta", "batir", "bazar", "beber", 
    "bella", "bello", "besar", "bicho", "blusa", "bocas", "bolsa", "bolso", "bomba", "borde", 
    "botas", "boton", "boxeo", "bravo", "brazo", "breve", "brisa", "broma", "brote", "bruja", 
    "brujo", "bruto", "bueno", "bulto", "buque", "burla", "burro", "busca", "busto", "caber", 
    "cable", "cabra", "cacao", "caida", "caido", "caldo", "calle", "calma", "calor", "calvo", 
    "campo", "canal", "canoa", "canta", "cante", "canto", "capaz", "carga", "cargo", "carne", 
    "carpa", "carro", "carta", "casar", "casas", "casco", "causa", "cazar", "cejas", "celda", 
    "cenar", "cerdo", "cerro", "cesar", "cesta", "cetro", "chica", "chico", "chile", "china", 
    "ciclo", "cielo", "cifra", "cinco", "cinta", "circo", "citar", "civil", "clara", "claro", 
    "clase", "clave", "clavo", "clima", "cobra", "cobre", "coche", "color", "comer", "copia", 
    "coral", "corre", "corta", "corte", "corto", "cosas", "coser", "costa", "crear", "crece", 
    "creer", "crema", "crian", "criba", "cruce", "crudo", "cruel", "cruza", "cuero", "cueva", 
    "cuida", "culpa", "culto", "cuota", "curar", "curso", "curva", "danza", "deber", "debil", 
    "decir", "dejar", "densa", "denso", "desde", "desea", "deseo", "deuda", "diana", "dicen", 
    "dicha", "dicho", "dieta", "digna", "digno", "diosa", "disco", "dobla", "doble", "dolor", 
    "donde", "dorso", "dosis", "drama", "ducha", "dudar", "duena", "dueno", "dulce", "echar", 
    "elige", "ellas", "ellos", "emite", "enano", "enero", "enojo", "entra", "entre", "envio", 
    "error", "espia", "estar", "estos", "estoy", "etapa", "evita", "exito", "facil", "falda", 
    "falla", "fallo", "falsa", "falta", "fango", "farol", "farsa", "fatal", "fauna", "favor", 
    "fecha", "feliz", "feria", "firma", "firme", "flaco", "flojo", "flora", "flota", "fondo", 
    "forma", "freno", "fresa", "frito", "fruta", "fruto", "fuego", "fuera", "fugaz", "fumar", 
    "furia", "gafas", "gallo", "ganar", "garra", "garza", "gasta", "gasto", "gente", "gesto", 
    "girar", "globo", "golpe", "gordo", "gorra", "gozar", "grado", "grano", "grasa", "grave", 
    "grito", "grupo", "guapa", "guapo", "guiar", "gusta", "gusto", "haber", "habil", "habla", 
    "hacer", "hacha", "hacia", "halla", "hasta", "hecho", "herir", "hielo", "hiena", "hogar", 
    "hondo", "hongo", "honor", "hotel", "huevo", "huida", "humor", "ideal", "igual", "islas", 
    "jamon", "jarra", "jaula", "joven", "juega", "juego", "jueza", "jugar", "junio", "junta", 
    "junto", "justo", "labio", "labor", "ladra", "leche", "legal", "lejos", "lento", "leona", 
    "letra", "libra", "libre", "libro", "lider", "ligar", "limon", "linda", "lindo", "linea", 
    "listo", "llama", "llave", "llega", "llena", "lleva", "llora", "local", "logra", "logro", 
    "lucha", "lucir", "luego", "lugar", "lunes", "madre", "magia", "manda", "mango", "mania", 
    "manta", "marca", "marco", "marea", "marzo", "matar", "mayor", "media", "medio", "mejor", 
    "menor", "menos", "menta", "mente", "mesas", "metal", "meter", "metro", "miedo", "milla", 
    "mirar", "mismo", "mitad", "mojar", "molde", "monja", "monta", "monte", "moral", "morir", 
    "mosca", "motor", "mover", "mucho", "muela", "muere", "mueve", "mujer", "multa", "mundo", 
    "museo", "musgo", "nacer", "nadar", "nariz", "necio", "negar", "negro", "nieta", "nieto", 
    "nieve", "nivel", "noble", "noche", "nopal", "norte", "notar", "novia", "novio", "nubes", 
    "nueve", "nuevo", "nunca", "obras", "ocaso", "ocupa", "odiar", "oeste", "oliva", "olivo", 
    "opera", "opina", "orden", "oreja", "osado", "otoño", "oveja", "pacto", "padre", "pagar", 
    "palma", "panda", "panza", "papel", "parar", "pared", "parte", "pasar", "paseo", "pasta", 
    "pasto", "patio", "pausa", "pecar", "pecho", "pedir", "pegar", "peine", "pelar", "pelea", 
    "penal", "perla", "perro", "pesar", "pesca", "peste", "piano", "picar", "pieza", "pilar", 
    "pinta", "pinto", "pista", "pizza", "placa", "plano", "plata", "plato", "playa", "plaza", 
    "plazo", "pleno", "plomo", "pluma", "pobre", "poder", "poema", "poeta", "pollo", "polvo", 
    "poner", "porta", "posee", "poste", "potro", "prado", "presa", "preso", "prima", "primo", 
    "prisa", "prosa", "pudor", "puede", "pulga", "pulpo", "pulso", "punta", "punto", "quedo", 
    "queja", "quema", "queso", "quien", "quita", "radio", "raido", "rampa", "rango", "rapto", 
    "rasca", "raton", "rayas", "razon", "recto", "redes", "regla", "reina", "reino", "reloj", 
    "renta", "resto", "reyes", "rezar", "riego", "rigor", "rival", "rison", "ritmo", "robar", 
    "roble", "robot", "rodeo", "rogar", "rollo", "rompe", "ronco", "ronda", "rosas", "abeto", 
    "rubia", "rubio", "rueda", "ruego", "rugir", "ruido", "ruina", "rumba", "rumbo", "rural", 
    "saber", "sabio", "sabor", "sacar", "saldo", "salir", "salon", "salsa", "salta", "salto", 
    "salud", "salva", "salvo", "sanar", "santa", "santo", "sauce", "secar", "sello", "selva", 
    "senda", "senil", "seria", "serie", "serio", "sesgo", "senal", "senas", "senor", "short", 
    "sidra", "siete", "siglo", "signo", "sigue", "silla", "sirve", "sismo", "sitio", "sobra", 
    "sobre", "socio", "solar", "soler", "sonar", "sopla", "sordo", "sonar", "suave", "subir", 
    "sucia", "sucio", "sudar", "suela", "suelo", "suena", "sueno", "suena", "suele", "sueño", 
    "sufre", "sumar", "super", "surge", "susto", "tabla", "tacto", "talla", "tango", "tanto", 
    "tapar", "tarde", "tardo", "tarea", "tarro", "tarta", "tazas", "techo", "tecla", "tedio", 
    "tejer", "temer", "temor", "tenaz", "tener", "tenis", "tenor", "terco", "texto", "tiene", 
    "tigre", "tinta", "tinte", "tirar", "tocar", "tomar", "tonto", "toque", "tordo", "torpe", 
    "torre", "torso", "toser", "total", "traer", "trago", "traje", "trama", "trata", "trato", 
    "trazo", "tribu", "trigo", "trono", "tropa", "trote", "trozo", "truco", "tumba", "tumor", 
    "tunel", "turno", "tutor", "unico", "unido", "union", "usaba", "usada", "usado", "usted", 
    "usual", "utero", "vacas", "vacia", "vacio", "vagar", "valer", "valle", "valor", "vamos", 
    "vapor", "vasto", "veces", "vejez", "velar", "veloz", "vemos", "vende", "vengo", "venir", 
    "venta", "veraz", "verbo", "verde", "verso", "viaja", "viaje", "vicio", "video", "vieja", 
    "viejo", "viene", "vigia", "vigor", "villa", "vimos", "virus", "visor", "vista", "viste", 
    "visto", "viuda", "viudo", "vivir", "vocal", "volar", "votar", "vuela", "vuelo", "yendo", 
    "yerba", "yogur", "zarza", "zorro", # 754
    
    # Ampliación extra (palabras probadas no existentes)
    "apodo", "riada", "balsa", "aguas", "ahoga", "iglus", "aereo", "braga", "tanga"
    ]
    
print(f"Tamaño de la lista de Wordless: {len(WORD_LIST)} palabras")

# Funciones de utilidad para wordless
def choose_word():
    return random.choice(WORD_LIST)

def evaluate_guess(guess, secret):
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
                sleep(3)
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
