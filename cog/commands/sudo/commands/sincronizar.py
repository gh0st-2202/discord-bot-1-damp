import discord
from discord import app_commands
import os
import asyncio
import traceback
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

def setup_command(sudo_group):
    """Configura el comando sincronizar en el grupo sudo"""
    
    @sudo_group.command(name="sincronizar", description="Sincroniza los comandos de barra con Discord")
    @app_commands.describe(
        ambito="Ámbito de sincronización",
        guild_id="ID del servidor para sincronizar (solo para 'servidor')"
    )
    @app_commands.choices(ambito=[
        app_commands.Choice(name="Global (todos los servidores)", value="global"),
        app_commands.Choice(name="Este servidor", value="guild"),
        app_commands.Choice(name="Servidor específico", value="specific"),
        app_commands.Choice(name="Ver comandos cargados", value="list"),
        app_commands.Choice(name="Limpiar comandos globales", value="clear_global"),
    ])
    async def sincronizar(
        interaction: discord.Interaction,
        ambito: app_commands.Choice[str],
        guild_id: Optional[str] = None
    ):
        """
        Comando para sincronizar los comandos de barra con Discord
        
        Opciones:
        - global: Sincroniza globalmente (tarda hasta 1 hora en propagarse)
        - guild: Sincroniza solo en este servidor (instantáneo)
        - specific: Sincroniza en un servidor específico por ID
        - list: Muestra los comandos actualmente cargados
        - clear_global: Elimina todos los comandos globales
        """
        
        # Verificar que el usuario sea administrador
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="⛔ Permiso Denegado",
                description="Necesitas permisos de administrador para usar este comando.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Mostrar que estamos procesando
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            # Obtener el árbol de comandos
            tree = interaction.client.tree
            
            # Procesar según la opción elegida
            ambito_value = ambito.value
            
            if ambito_value == "global":
                # Sincronización global
                embed = discord.Embed(
                    title="🌍 Sincronización Global",
                    description="Iniciando sincronización global de comandos...",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="⚠️ Advertencia",
                    value="La sincronización global puede tardar **hasta 1 hora** en propagarse a todos los servidores.",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Sincronizar globalmente
                try:
                    commands = await tree.sync()
                    
                    success_embed = discord.Embed(
                        title="✅ Sincronización Global Completada",
                        description=f"Se han sincronizado **{len(commands)}** comandos globalmente.",
                        color=discord.Color.green()
                    )
                    success_embed.add_field(
                        name="Comandos Sincronizados",
                        value=f"`{', '.join([cmd.name for cmd in commands[:10]])}`" + 
                              (f"\n... y {len(commands) - 10} más" if len(commands) > 10 else ""),
                        inline=False
                    )
                    success_embed.add_field(
                        name="Tiempo de Propagación",
                        value="Los cambios se reflejarán en todos los servidores en los próximos minutos/hora.",
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=success_embed, ephemeral=True)
                    
                except Exception as e:
                    error_embed = discord.Embed(
                        title="❌ Error en Sincronización Global",
                        description=f"```{str(e)}```",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            
            elif ambito_value == "guild":
                # Sincronización en este servidor
                embed = discord.Embed(
                    title="🏠 Sincronización en Este Servidor",
                    description=f"Sincronizando comandos en **{interaction.guild.name}**...",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Sincronizar en el servidor actual
                try:
                    guild = interaction.guild
                    tree.copy_global_to(guild=guild)
                    commands = await tree.sync(guild=guild)
                    
                    success_embed = discord.Embed(
                        title="✅ Sincronización Completada",
                        description=f"Comandos sincronizados en **{guild.name}**",
                        color=discord.Color.green()
                    )
                    success_embed.add_field(
                        name="Comandos Sincronizados",
                        value=f"**{len(commands)}** comandos disponibles",
                        inline=False
                    )
                    success_embed.add_field(
                        name="ID del Servidor",
                        value=f"`{guild.id}`",
                        inline=True
                    )
                    success_embed.add_field(
                        name="Miembros",
                        value=f"`{guild.member_count}`",
                        inline=True
                    )
                    
                    # Listar comandos por grupos
                    grouped_commands = {}
                    for cmd in commands:
                        if isinstance(cmd, app_commands.Command):
                            group = "Comandos Principales"
                        elif isinstance(cmd, app_commands.Group):
                            group = f"Grupo: {cmd.name}"
                        else:
                            group = "Otros"
                        
                        if group not in grouped_commands:
                            grouped_commands[group] = []
                        grouped_commands[group].append(cmd.name)
                    
                    for group, cmd_names in grouped_commands.items():
                        success_embed.add_field(
                            name=group,
                            value=f"`{', '.join(cmd_names[:5])}`" + 
                                  (f"\n... y {len(cmd_names) - 5} más" if len(cmd_names) > 5 else ""),
                            inline=False
                        )
                    
                    await interaction.followup.send(embed=success_embed, ephemeral=True)
                    
                except Exception as e:
                    error_embed = discord.Embed(
                        title="❌ Error en Sincronización",
                        description=f"```{str(e)}```",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            
            elif ambito_value == "specific":
                # Sincronización en servidor específico
                if not guild_id or not guild_id.isdigit():
                    embed = discord.Embed(
                        title="❌ ID Inválido",
                        description="Por favor, proporciona un ID de servidor válido (solo números).",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                guild_id_int = int(guild_id)
                
                embed = discord.Embed(
                    title="🎯 Sincronización en Servidor Específico",
                    description=f"Sincronizando comandos en servidor ID: `{guild_id}`...",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                try:
                    # Intentar obtener el servidor
                    guild = interaction.client.get_guild(guild_id_int)
                    if not guild:
                        embed = discord.Embed(
                            title="❌ Servidor No Encontrado",
                            description=f"No se encontró el servidor con ID `{guild_id}`.\n\n"
                                      f"Asegúrate de que:\n"
                                      f"1. El bot está en ese servidor\n"
                                      f"2. El ID es correcto",
                            color=discord.Color.red()
                        )
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return
                    
                    # Sincronizar en el servidor específico
                    tree.copy_global_to(guild=guild)
                    commands = await tree.sync(guild=guild)
                    
                    success_embed = discord.Embed(
                        title="✅ Sincronización Exitosa",
                        description=f"Comandos sincronizados en **{guild.name}**",
                        color=discord.Color.green()
                    )
                    success_embed.add_field(
                        name="Comandos Sincronizados",
                        value=f"**{len(commands)}** comandos",
                        inline=True
                    )
                    success_embed.add_field(
                        name="ID del Servidor",
                        value=f"`{guild.id}`",
                        inline=True
                    )
                    success_embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                    
                    await interaction.followup.send(embed=success_embed, ephemeral=True)
                    
                except Exception as e:
                    error_embed = discord.Embed(
                        title="❌ Error en Sincronización",
                        description=f"```{str(e)}```",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            
            elif ambito_value == "list":
                # Listar comandos cargados
                embed = discord.Embed(
                    title="📋 Comandos Cargados",
                    description="Lista de todos los comandos de barra registrados",
                    color=discord.Color.blue()
                )
                
                # Comandos globales
                global_commands = tree.get_commands()
                if global_commands:
                    global_list = []
                    for cmd in global_commands:
                        if isinstance(cmd, app_commands.Command):
                            global_list.append(f"• `/{cmd.name}` - {cmd.description}")
                        elif isinstance(cmd, app_commands.Group):
                            # Para grupos, listar subcomandos
                            global_list.append(f"**Grupo: `/{cmd.name}`**")
                            for subcmd in cmd.commands:
                                global_list.append(f"  ↳ `/{cmd.name} {subcmd.name}` - {subcmd.description}")
                    
                    embed.add_field(
                        name="🌍 Comandos Globales",
                        value="\n".join(global_list[:20]) + 
                              (f"\n... y {len(global_list) - 20} más" if len(global_list) > 20 else ""),
                        inline=False
                    )
                
                # Comandos por servidor (solo este)
                try:
                    guild_commands = tree.get_commands(guild=interaction.guild)
                    if guild_commands:
                        guild_list = []
                        for cmd in guild_commands:
                            if isinstance(cmd, app_commands.Command):
                                guild_list.append(f"• `/{cmd.name}`")
                            elif isinstance(cmd, app_commands.Group):
                                guild_list.append(f"**Grupo: `/{cmd.name}`**")
                        
                        if guild_list:
                            embed.add_field(
                                name=f"🏠 Comandos en {interaction.guild.name}",
                                value="\n".join(guild_list[:10]),
                                inline=False
                            )
                except:
                    pass
                
                # Estadísticas
                total_commands = len(tree._state._command_tree.get_commands())
                embed.add_field(
                    name="📊 Estadísticas",
                    value=(
                        f"**Comandos totales:** {total_commands}\n"
                        f"**Grupos cargados:** {len([c for c in global_commands if isinstance(c, app_commands.Group)])}\n"
                        f"**Servidores con bot:** {len(interaction.client.guilds)}"
                    ),
                    inline=False
                )
                
                embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            
            elif ambito_value == "clear_global":
                # Limpiar comandos globales
                embed = discord.Embed(
                    title="⚠️ ¡ADVERTENCIA!",
                    description="Estás a punto de **ELIMINAR TODOS** los comandos globales.\n\n"
                              "Esta acción es **IRREVERSIBLE** y eliminará los comandos de todos los servidores.",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="Consecuencias",
                    value="• Todos los comandos dejarán de funcionar\n"
                          "• Tendrás que volver a sincronizar\n"
                          "• Los cambios tardarán hasta 1 hora en propagarse",
                    inline=False
                )
                
                # Crear vista con botones de confirmación
                class ConfirmView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=60)
                        self.confirmed = False
                    
                    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.danger)
                    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                        self.confirmed = True
                        await self.handle_clear(interaction)
                        self.stop()
                    
                    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
                    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                        embed = discord.Embed(
                            title="✅ Operación Cancelada",
                            description="No se han eliminado los comandos.",
                            color=discord.Color.green()
                        )
                        await interaction.response.edit_message(embed=embed, view=None)
                        self.stop()
                    
                    async def handle_clear(self, interaction: discord.Interaction):
                        try:
                            # Limpiar comandos globales
                            tree.clear_commands(guild=None)
                            await tree.sync()
                            
                            embed = discord.Embed(
                                title="🗑️ Comandos Globales Eliminados",
                                description="Todos los comandos globales han sido eliminados.",
                                color=discord.Color.green()
                            )
                            embed.add_field(
                                name="Siguientes Pasos",
                                value="Para restaurar los comandos, usa `/sudo sincronizar` de nuevo.",
                                inline=False
                            )
                            
                            await interaction.response.edit_message(embed=embed, view=None)
                            
                        except Exception as e:
                            error_embed = discord.Embed(
                                title="❌ Error al Limpiar",
                                description=f"```{str(e)}```",
                                color=discord.Color.red()
                            )
                            await interaction.response.edit_message(embed=error_embed, view=None)
                
                await interaction.followup.send(embed=embed, view=ConfirmView(), ephemeral=True)
        
        except Exception as e:
            # Manejo de errores generales
            error_embed = discord.Embed(
                title="❌ Error Inesperado",
                description="Ocurrió un error al procesar el comando.",
                color=discord.Color.red()
            )
            error_embed.add_field(
                name="Detalles del Error",
                value=f"```{str(e)[:1000]}```",
                inline=False
            )
            
            # Log del error completo
            print(f"❌ Error en comando sincronizar:")
            traceback.print_exc()
            
            await interaction.followup.send(embed=error_embed, ephemeral=True)
