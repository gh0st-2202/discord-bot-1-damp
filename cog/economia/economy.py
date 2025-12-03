import discord
from discord.ext import commands
from discord import app_commands
import os
import importlib
import sys

# Grupo de comandos de economía
economy_group = app_commands.Group(
    name="economy", 
    description="Comandos de economía y gestión de dinero",
    default_permissions=None
)

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loaded_commands = []

    async def load_economy_commands(self):
        """Carga automáticamente todos los comandos de la carpeta economy"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        economy_commands_path = os.path.join(current_dir, "economy")
        
        if not os.path.exists(economy_commands_path):
            print("❌ No se encuentra la carpeta economy")
            return

        if economy_commands_path not in sys.path:
            sys.path.append(economy_commands_path)

        for filename in os.listdir(economy_commands_path):
            if filename.endswith(".py") and filename not in ["__init__.py", "economy.py"]:
                module_name = filename[:-3]
                try:
                    # Importar usando importlib con ruta absoluta
                    spec = importlib.util.spec_from_file_location(
                        module_name, 
                        os.path.join(economy_commands_path, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'setup_command'):
                        module.setup_command(economy_group, self)
                        self.loaded_commands.append(module_name)
                        print(f"✅ Comando economy cargado: {module_name}")
                    else:
                        print(f"⚠️  Módulo {module_name} no tiene función setup_command")
                        
                except Exception as e:
                    print(f"❌ Error al cargar {filename}: {e}")

    async def cog_load(self):
        await self.load_economy_commands()

async def setup(bot):
    bot.tree.add_command(economy_group)
    economy_cog = EconomyCog(bot)
    await bot.add_cog(economy_cog)
