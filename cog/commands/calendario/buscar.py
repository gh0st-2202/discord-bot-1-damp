import discord
from discord import app_commands

async def search_events(interaction: discord.Interaction, calendar_sync, busqueda: str):
    """Busca eventos por palabra clave"""
    calendar = calendar_sync
    # Asegurar sincronización antes de mostrar eventos
    await calendar.sync_events()
    
    results = []
    for event in calendar.events:
        if (busqueda.lower() in event['summary'].lower() or 
            busqueda.lower() in event['description'].lower()):
            results.append(event)
    
    if not results:
        embed = discord.Embed(
            title=f"🔍 Búsqueda: {busqueda}",
            description="❌ No se encontraron eventos",
            color=0xff0000
        )
        embed.set_footer(text="🔄 Sincronizado automáticamente")
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"🔍 Resultados para: {busqueda}",
        description=f"Se encontraron **{len(results)}** eventos",
        color=0x7289da
    )
    
    for event in results[:6]:
        emoji = "📚" if event['calendar'] == 'moodle' else "📝"
        date_str = event['start'].strftime('%d/%m/%Y %H:%M')
        embed.add_field(
            name=f"{emoji} {event['summary']}",
            value=f"**Fecha:** {date_str}\n**Calendario:** {event['calendar_name']}",
            inline=False
        )
    
    if len(results) > 6:
        embed.set_footer(text=f"🔄 Sincronizado | Mostrando 6 de {len(results)} resultados")
    else:
        embed.set_footer(text="🔄 Sincronizado automáticamente")
    
    await interaction.followup.send(embed=embed)

def setup_command(calendario_group, cog):
    """Configura el comando buscar en el grupo calendario"""
    
    @calendario_group.command(name="buscar", description="Busca eventos en todos los calendarios")
    @app_commands.describe(busqueda="Término de búsqueda")
    async def buscar(interaction: discord.Interaction, busqueda: str):
        await interaction.response.defer()
        await search_events(interaction, cog.calendar_sync, busqueda)
