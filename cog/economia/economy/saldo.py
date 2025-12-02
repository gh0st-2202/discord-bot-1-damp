import discord
from discord import app_commands
from typing import Optional
import sys
import os

# Agregar el directorio padre al path para importar desde economy.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar desde el módulo principal
from economy import get_player, supabase

def setup_command(economy_group, cog):
    """Configura el comando saldo en el grupo economy con parámetro opcional"""
    
    @economy_group.command(name="saldo", description="Muestra tu saldo o el de otro usuario")
    @app_commands.describe(usuario="Usuario cuyo saldo quieres ver (opcional)")
    async def saldo(interaction: discord.Interaction, usuario: Optional[discord.User] = None):
        target_user = usuario if usuario else interaction.user
        is_self = target_user.id == interaction.user.id
        
        try:
            player = await get_player(str(target_user.id), target_user.name)
            
            if not player:
                embed = discord.Embed(
                    title="❌ Error",
                    description="No se pudo obtener la información del usuario.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            if is_self:
                embed = discord.Embed(
                    title="💰 Tu Estado de Cuenta",
                    color=discord.Color.gold()
                )
                embed.add_field(name="👤 Usuario", value=interaction.user.mention, inline=True)
            else:
                embed = discord.Embed(
                    title=f"💰 Saldo de {target_user.display_name}",
                    color=discord.Color.blue()
                )
                embed.add_field(name="👤 Usuario", value=target_user.mention, inline=True)
                embed.add_field(name="🔍 Consultado por", value=interaction.user.mention, inline=True)
            
            embed.add_field(name="💵 Saldo", value=f"**{player['balance']:,}** monedas", inline=True)
            
            # Obtener ranking desde Supabase
            response = supabase.table("players").select("balance").order("balance", desc=True).execute()
            all_players = response.data if response.data else []
            
            if all_players:
                # Encontrar posición del jugador
                sorted_balances = sorted([p["balance"] for p in all_players], reverse=True)
                try:
                    rank = sorted_balances.index(player["balance"]) + 1
                except ValueError:
                    rank = len(sorted_balances) + 1
                
                total_players = len(all_players)
                embed.add_field(
                    name="🏆 Ranking", 
                    value=f"**#{rank}** de {total_players} jugadores", 
                    inline=True
                )
                
                # Calcular porcentaje del total de riqueza
                total_wealth = sum(p["balance"] for p in all_players) or 1
                wealth_percentage = (player["balance"] / total_wealth) * 100
                
                embed.add_field(
                    name="📊 Riqueza Global", 
                    value=f"**{wealth_percentage:.2f}%** del total", 
                    inline=True
                )
            else:
                embed.add_field(name="🏆 Ranking", value="**#1** de 1 jugador", inline=True)
                embed.add_field(name="📊 Riqueza Global", value="**100.00%** del total", inline=True)
            
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            if is_self:
                embed.set_footer(text="Usa /economy transferir para enviar dinero a otros")
            else:
                embed.set_footer(text=f"Información financiera de {target_user.display_name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=is_self)
            
        except Exception as e:
            print(f"Error en saldo: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ha ocurrido un error al obtener el saldo.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
