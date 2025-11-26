import discord
from discord import app_commands
from datetime import datetime

async def send_today_events(interaction: discord.Interaction, calendar_sync):
    """Envía solo los eventos de hoy"""
    calendar = calendar_sync
    # Asegurar sincronización antes de mostrar eventos
    await calendar.sync_events()
    
    today_events = calendar.get_events_today()
    
    if not today_events:
        embed = discord.Embed(
            title="📅 Eventos de Hoy",
            description="✅ No hay eventos programados para hoy",
            color=0x00ff00
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Separar eventos por calendario
    moodle_events = [e for e in today_events if e['calendar'] == 'moodle']
    google_events = [e for e in today_events if e['calendar'] == 'google']
    
    embed = discord.Embed(
        title=f"📅 Eventos de Hoy ({len(today_events)})",
        color=0xffa500,
        timestamp=datetime.now()
    )
    
    # Eventos de Moodle
    if moodle_events:
        moodle_text = ""
        for event in moodle_events:
            start_time = event['start'].strftime('%H:%M')
            moodle_text += f"**⏰ {start_time}** - {event['summary']}\n"
        embed.add_field(
            name=f"📚 Tareas ({len(moodle_events)})",
            value=moodle_text,
            inline=False
        )
    
    # Eventos de Google Calendar
    if google_events:
        google_text = ""
        for event in google_events:
            start_time = event['start'].strftime('%H:%M')
            google_text += f"**⏰ {start_time}** - {event['summary']}\n"
        embed.add_field(
            name=f"📅 Exámenes ({len(google_events)})",
            value=google_text,
            inline=False
        )
    
    embed.set_footer(text="🔄 Sincronizado automáticamente")
    await interaction.followup.send(embed=embed)

def setup_command(calendario_group, cog):
    """Configura el comando hoy en el grupo calendario"""
    
    @calendario_group.command(name="hoy", description="Muestra los eventos de hoy")
    async def hoy(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await send_today_events(interaction, cog.calendar_sync)
