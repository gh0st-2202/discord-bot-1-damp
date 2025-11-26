import discord
from discord import app_commands
from discord.ext import commands
import os
import importlib
import sys

sudo_group = app_commands.Group(
    name="sudo", 
    description="Comandos de administrador para gestión del sistema",
    default_permissions=discord.Permissions(administrator=True)
)

class SudoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loaded_commands = []

    async def load_sudo_commands_recursive(self, directory):
        """Carga recursivamente todos los comandos de la carpeta sudo y subcarpetas"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sudo_commands_path = os.path.join(current_dir, "sudo")
        
        if not os.path.exists(sudo_commands_path):
            print("❌ No se encuentra la carpeta sudo")
            return

        if sudo_commands_path not in sys.path:
            sys.path.append(sudo_commands_path)

        # Recorrer recursivamente todas las subcarpetas
        for root, dirs, files in os.walk(sudo_commands_path):
            for filename in files:
                if filename.endswith(".py") and filename not in ["__init__.py", "sudo.py"]:
                    # Obtener la ruta relativa para el import
                    rel_path = os.path.relpath(os.path.join(root, filename), sudo_commands_path)
                    module_path = rel_path.replace(os.path.sep, '.').replace('.py', '')
                    
                    try:
                        # Importar el módulo
                        module = importlib.import_module(module_path)
                        importlib.reload(module)
                        
                        if hasattr(module, 'setup_command'):
                            module.setup_command(sudo_group)
                            self.loaded_commands.append(module_path)
                            print(f"✅ Comando sudo cargado: {module_path}")
                        else:
                            print(f"⚠️  Módulo {module_path} no tiene función setup_command")
                            
                    except Exception as e:
                        print(f"❌ Error al cargar {filename}: {e}")

    async def cog_load(self):
        await self.load_sudo_commands_recursive("./cog/commands/sudo")

async def setup(bot):
    bot.tree.add_command(sudo_group)
    sudo_cog = SudoCog(bot)
    await bot.add_cog(sudo_cog)
