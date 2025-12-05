import discord
from discord.ext import commands
from discord import app_commands
import os
import importlib
import sys
import random
from datetime import datetime
from discord.ext import tasks
from supabase import create_client
import asyncio
import json
from pathlib import Path

# Obtener credenciales de Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Faltan variables de entorno SUPABASE_URL o SUPABASE_KEY")

# Inicializar cliente de Supabase
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Cliente Supabase inicializado correctamente")
except Exception as e:
    print(f"❌ Error al inicializar Supabase: {e}")
    supabase = None

# Grupo de comandos de criptomonedas
crypto_group = app_commands.Group(
    name="crypto",
    description="Sistema de trading de criptomonedas",
    default_permissions=None
)

# Configuración de criptomonedas para actualización
CRYPTO_CONFIG = {
    "BTC": {
        "name": "BitCord",
        "emoji": "₿",
        "base_price": 10000,
        "volatility": (0.98, 1.02),
        "min_price": 5000,
        "max_price": 20000,
        "color": 0xF7931A
    },
    "ETH": {
        "name": "Etherium", 
        "emoji": "Ξ",
        "base_price": 3000,
        "volatility": (0.95, 1.05),
        "min_price": 1500,
        "max_price": 6000,
        "color": 0x627EEA
    },
    "DOG": {
        "name": "DoggoCoin",
        "emoji": "🐕",
        "base_price": 50,
        "volatility": (0.85, 1.15),
        "min_price": 10,
        "max_price": 200,
        "color": 0xF2A900
    }
}

# Diccionario para almacenar precios originales (en memoria temporalmente)
PRICE_HISTORY_FILE = "crypto_price_history.json"

def load_price_history():
    """Carga el historial de precios desde archivo JSON"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        history_path = os.path.join(current_dir, PRICE_HISTORY_FILE)
        
        if os.path.exists(history_path):
            with open(history_path, 'r') as f:
                return json.load(f)
        else:
            # Crear estructura inicial
            history = {
                "BTC": {"original": 10000, "current": 10000, "change_percent": 0.0},
                "ETH": {"original": 3000, "current": 3000, "change_percent": 0.0},
                "DOG": {"original": 50, "current": 50, "change_percent": 0.0}
            }
            with open(history_path, 'w') as f:
                json.dump(history, f, indent=2)
            return history
    except Exception as e:
        print(f"❌ Error al cargar historial de precios: {e}")
        return {
            "BTC": {"original": 10000, "current": 10000, "change_percent": 0.0},
            "ETH": {"original": 3000, "current": 3000, "change_percent": 0.0},
            "DOG": {"original": 50, "current": 50, "change_percent": 0.0}
        }

def save_price_history(history):
    """Guarda el historial de precios en archivo JSON"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        history_path = os.path.join(current_dir, PRICE_HISTORY_FILE)
        
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"❌ Error al guardar historial de precios: {e}")

def update_price_history_sync(crypto, new_price):
    """Actualiza el historial de precios y calcula el porcentaje de cambio"""
    history = load_price_history()
    
    if crypto not in history:
        # Si es la primera vez, establecer original y actual
        history[crypto] = {
            "original": new_price,
            "current": new_price,
            "change_percent": 0.0
        }
    else:
        # Obtener precio original (si existe) o usar el actual como original
        original_price = history[crypto].get("original", new_price)
        previous_price = history[crypto].get("current", new_price)
        
        # Calcular cambio porcentual desde el ORIGINAL (no desde el anterior)
        change_percent = ((new_price - original_price) / original_price * 100) if original_price > 0 else 0
        
        # Si el cambio es muy pequeño (menos de 1%), mantener el precio original
        # Esto simula que el "precio original" es el de la última variación significativa
        if abs(change_percent) < 1.0:
            # No actualizar el precio original, solo el actual
            history[crypto] = {
                "original": original_price,
                "current": new_price,
                "change_percent": change_percent
            }
        else:
            # Cambio significativo, actualizar ambos
            history[crypto] = {
                "original": new_price,  # El nuevo precio se convierte en el "original"
                "current": new_price,
                "change_percent": 0.0  # Reiniciar contador
            }
    
    save_price_history(history)
    return history[crypto]["change_percent"]

# ============ FUNCIONES DE LECTURA DE PRECIOS ============
def get_current_prices_sync():
    """Obtiene los precios actuales DESDE Supabase (SOLO LECTURA)"""
    if not supabase:
        print("❌ Cliente Supabase no inicializado")
        return {crypto: config["base_price"] for crypto, config in CRYPTO_CONFIG.items()}
    
    try:
        response = supabase.table('crypto_current_prices').select('*').execute()
        
        if not response.data:
            print("⚠️ No hay precios en la base de datos")
            return {crypto: config["base_price"] for crypto, config in CRYPTO_CONFIG.items()}
        
        prices = {}
        for item in response.data:
            prices[item['crypto']] = int(item['price'])  # Convertir a ENTERO
        
        # Asegurar que todas las criptomonedas estén presentes
        for crypto in ["BTC", "ETH", "DOG"]:
            if crypto not in prices:
                print(f"⚠️  {crypto} no encontrado en BD, usando valor base")
                prices[crypto] = CRYPTO_CONFIG[crypto]["base_price"]
        
        return prices
    except Exception as e:
        print(f"❌ Error al obtener precios: {e}")
        return {crypto: config["base_price"] for crypto, config in CRYPTO_CONFIG.items()}

# ============ FUNCIONES DE ACTUALIZACIÓN DE PRECIOS ============
def update_crypto_price_sync(crypto, new_price):
    """Actualiza el precio de una criptomoneda en Supabase"""
    if not supabase:
        print("❌ Cliente Supabase no inicializado")
        return
    
    try:
        # Convertir a entero
        new_price = int(round(new_price))
        
        # Actualizar la tabla de precios actuales
        supabase.table('crypto_current_prices').update({
            'price': new_price,
            'last_update': datetime.now().isoformat()
        }).eq('crypto', crypto).execute()
        
        return new_price
        
    except Exception as e:
        print(f"❌ Error al actualizar precio {crypto}: {e}")
        return None

def update_prices_sync():
    """Actualiza todos los precios según volatilidad, partiendo de los precios existentes"""
    if not supabase:
        print("❌ Cliente Supabase no inicializado")
        return get_current_prices_sync()
    
    try:
        # LEER precios actuales de la BD
        prices = get_current_prices_sync()
        
        changes = {}
        updated_count = 0
        
        for crypto, config in CRYPTO_CONFIG.items():
            current_price = prices.get(crypto, config["base_price"])
            
            # Asegurar que tenemos un precio válido
            if not current_price or current_price <= 0:
                current_price = config["base_price"]
            
            # Calcular nuevo precio con volatilidad
            min_vol, max_vol = config["volatility"]
            change = random.uniform(min_vol, max_vol)
            new_price = current_price * change
            
            # Aplicar límites y convertir a entero
            new_price = max(config["min_price"], min(config["max_price"], new_price))
            new_price = int(round(new_price))
            
            # Solo actualizar si hay cambio
            if new_price != current_price:
                updated_price = update_crypto_price_sync(crypto, new_price)
                if updated_price:
                    # Calcular y guardar cambio porcentual en el historial
                    change_percent = update_price_history_sync(crypto, updated_price)
                    
                    changes[crypto] = {
                        'old': current_price,
                        'new': updated_price,
                        'change_percent': change_percent
                    }
                    updated_count += 1
        
        # Si hubo cambios, mostrar mensaje detallado
        if changes:
            print(f"\n{'='*50}")
            print(f"🔄 ACTUALIZACIÓN DE PRECIOS ({datetime.now().strftime('%H:%M:%S')})")
            print(f"{'='*50}")
            
            for crypto, data in changes.items():
                emoji = CRYPTO_CONFIG[crypto]["emoji"]
                change_emoji = "📈" if data['change_percent'] >= 0 else "📉"
                print(f"{emoji} {crypto}: {data['old']:,} → {data['new']:,} ({data['change_percent']:+.1f}%) {change_emoji}")
            
            print(f"{'='*50}")
            print(f"✅ {updated_count} de 3 precios actualizados\n")
        
        return get_current_prices_sync()
        
    except Exception as e:
        print(f"❌ Error al actualizar precios: {e}")
        return get_current_prices_sync()

# ============ TAREA DE ACTUALIZACIÓN (CADA 5 MINUTOS) ============
@tasks.loop(minutes=5)
async def update_prices_task():
    """Actualiza precios cada 5 minutos con mensaje detallado"""
    try:
        print(f"\n⏰ Iniciando actualización programada ({datetime.now().strftime('%H:%M:%S')})...")
        prices = update_prices_sync()
        print(f"✅ Precios actuales: BTC={prices['BTC']:,}, ETH={prices['ETH']:,}, DOG={prices['DOG']:,}")
    except Exception as e:
        print(f"❌ Error en tarea de actualización: {e}")

# ============ COG PRINCIPAL ============
class CryptoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loaded_commands = []
        
    async def load_crypto_commands(self):
        """Carga automáticamente todos los comandos de la carpeta crypto"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        crypto_commands_path = os.path.join(current_dir, "crypto")
        
        if not os.path.exists(crypto_commands_path):
            os.makedirs(crypto_commands_path, exist_ok=True)
            print("📁 Carpeta crypto creada")
            
            # Crear archivos de comandos básicos si no existen
            from pathlib import Path
            Path(os.path.join(crypto_commands_path, "__init__.py")).touch()
            
            print("⚠️  La carpeta crypto está vacía. Crea los comandos en:")
            print(f"   {crypto_commands_path}/")
            return

        if crypto_commands_path not in sys.path:
            sys.path.append(crypto_commands_path)

        for filename in os.listdir(crypto_commands_path):
            if filename.endswith(".py") and filename not in ["__init__.py", "crypto.py"]:
                module_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(
                        module_name, 
                        os.path.join(crypto_commands_path, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'setup_command'):
                        module.setup_command(crypto_group, self)
                        self.loaded_commands.append(module_name)
                        print(f"✅ Comando crypto cargado: {module_name}")
                    else:
                        print(f"⚠️  Módulo {module_name} no tiene función setup_command")
                        
                except Exception as e:
                    print(f"❌ Error al cargar {filename}: {e}")

    async def cog_load(self):
        """Se ejecuta cuando el cog se carga"""
        print("🔄 Inicializando sistema crypto...")
        
        # Verificar conexión y precios
        try:
            prices = get_current_prices_sync()
            print(f"📊 Precios iniciales en BD: BTC={prices['BTC']:,}, ETH={prices['ETH']:,}, DOG={prices['DOG']:,}")
        except Exception as e:
            print(f"⚠️  No se pudieron leer precios iniciales: {e}")
        
        # Esperar antes de iniciar la tarea
        await asyncio.sleep(5)
        
        # Iniciar actualización de precios CADA 5 MINUTOS
        if not update_prices_task.is_running():
            update_prices_task.start()
            print("✅ Tarea de actualización de precios iniciada (cada 5 minutos)")
        
        # Cargar comandos
        await self.load_crypto_commands()
        
        if self.loaded_commands:
            print(f"✅ Sistema crypto listo. Comandos cargados: {', '.join(self.loaded_commands)}")
        else:
            print("⚠️  Sistema crypto activo pero sin comandos. Añade comandos en cog/economia/crypto/")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Cuando el bot está listo"""
        # Opcional: Forzar una actualización inicial
        await asyncio.sleep(10)
        print("🔍 Forzando primera actualización de precios...")
        update_prices_sync()

async def setup(bot):
    """Setup del cog"""
    bot.tree.add_command(crypto_group)
    crypto_cog = CryptoCog(bot)
    await bot.add_cog(crypto_cog)
