import discord
from discord import app_commands
import os
import time
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
CHANNEL_LEADERBOARD_ID = 1430215076769435800

# Funciones de base de datos locales
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
        return None
    
    try:
        leaderboard = await get_leaderboard(10)
        await channel.purge()
        
        embed = discord.Embed(title="🏆 TABLA DE LÍDERES GLOBAL", color=discord.Color.gold())
        
        if not leaderboard:
            embed.description = "📭 No hay jugadores registrados todavía."
        else:
            for i, player in enumerate(leaderboard[:10], start=1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                embed.add_field(
                    name=f"{medal} {player['username']}", 
                    value=f"```{player['balance']:,} monedas```", 
                    inline=False
                )
        
        embed.set_footer(text="Actualizado manualmente por administración")
        await channel.send(embed=embed)
        
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando leaderboard: {e}")
        return None

def setup_command(sudo_group):
    """Configura el comando leaderboard en el grupo sudo"""
    
    @sudo_group.command(name="leaderboard", description="Actualiza manualmente el leaderboard global (solo admin)")
    async def leaderboard(interaction: discord.Interaction):
        # Mostrar mensaje de procesando
        await interaction.response.send_message("🔄 Actualizando leaderboard...", ephemeral=True)
        
        try:
            # Actualizar leaderboard
            success = await update_global_leaderboard(interaction.client)
            
            if success:
                # Obtener información adicional para el admin
                leaderboard_data = await get_leaderboard(5)
                total_response = supabase.table("players").select("balance").execute()
                total_players = len(total_response.data) if total_response.data else 0
                total_wealth = sum(p["balance"] for p in total_response.data) if total_response.data else 0
                
                # Crear embed de confirmación para el admin
                embed = discord.Embed(
                    title="✅ Leaderboard Actualizado",
                    description="El leaderboard global ha sido actualizado manualmente.",
                    color=discord.Color.green()
                )
                
                # Mostrar top 5 actual
                if leaderboard_data:
                    embed.add_field(
                        name="🏆 Top 5 Actual",
                        value="\n".join([f"**{i}.** {p['username']} - {p['balance']:,}" 
                                        for i, p in enumerate(leaderboard_data[:5], 1)]),
                        inline=False
                    )
                
                # Estadísticas
                embed.add_field(
                    name="📊 Estadísticas",
                    value=(
                        f"**Jugadores totales:** {total_players}\n"
                        f"**Riqueza total:** {total_wealth:,} monedas"
                    ),
                    inline=True
                )
                
                embed.add_field(
                    name="📈 Canal Actualizado",
                    value=f"<#{CHANNEL_LEADERBOARD_ID}>",
                    inline=True
                )
                
                embed.set_footer(text=f"Ejecutado por {interaction.user.display_name}")
                embed.timestamp = discord.utils.utcnow()
                
                await interaction.edit_original_response(content=None, embed=embed)
                
                # Log en consola
                print(f"✅ Leaderboard actualizado manualmente por {interaction.user.name} ({interaction.user.id})")
                
            else:
                error_embed = discord.Embed(
                    title="❌ Error",
                    description="No se pudo actualizar el leaderboard. Verifica:\n1. Que el canal existe\n2. Que el bot tiene permisos",
                    color=discord.Color.red()
                )
                error_embed.add_field(name="Canal ID", value=f"`{CHANNEL_LEADERBOARD_ID}`", inline=False)
                error_embed.add_field(name="Solución", value="Verifica que el canal con ese ID existe y el bot puede leer/escribir en él", inline=False)
                
                await interaction.edit_original_response(content=None, embed=error_embed)
                
        except Exception as e:
            print(f"❌ Error en comando leaderboard: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error Inesperado",
                description=f"```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(content=None, embed=error_embed)

# Versión alternativa con permisos explícitos usando decorador
def setup_command_with_check(sudo_group, cog):
    """Versión con chequeo explícito de permisos"""
    
    @sudo_group.command(name="leaderboard", description="Actualiza manualmente el leaderboard global")
    @app_commands.default_permissions(administrator=True)
    async def leaderboard(interaction: discord.Interaction):
        # Verificar permisos explícitamente (aunque el grupo sudo ya debería manejarlo)
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="⛔ Permiso Denegado",
                description="Necesitas permisos de administrador para usar este comando.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Resto del código igual...
        await interaction.response.send_message("🔄 Actualizando leaderboard...", ephemeral=True)
        
        try:
            success = await update_global_leaderboard(interaction.client)
            
            if success:
                embed = discord.Embed(
                    title="✅ Leaderboard Actualizado",
                    description=f"Leaderboard actualizado en <#{CHANNEL_LEADERBOARD_ID}>",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Ejecutado por {interaction.user.display_name}")
                await interaction.edit_original_response(content=None, embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"No se pudo actualizar el canal <#{CHANNEL_LEADERBOARD_ID}>",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(content=None, embed=embed)
                
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Error: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(content=None, embed=embed)
