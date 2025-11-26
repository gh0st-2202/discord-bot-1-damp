import discord
from discord import app_commands
from datetime import datetime, timedelta

async def send_exams_events(interaction: discord.Interaction, calendar_sync):
    """Muestra solo los eventos de Google Calendar (exámenes)"""
    calendar = calendar_sync
    # Asegurar sincronización antes de mostrar eventos
    await calendar.sync_events()
    
    exams_events = calendar.get_events_by_calendar('google', days=60)
    
    if not exams_events:
        embed = discord.Embed(
            title="📅 Exámenes",
            description="✅ No hay exámenes programados en los próximos 60 días",
            color=0x4285f4
        )
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="📅 Exámenes",
        description=f"**{len(exams_events)}** exámenes encontrados",
        color=0x4285f4,
        timestamp=datetime.now()
    )
    
    # Agrupar por mes
    events_by_month = {}
    for event in exams_events:
        month_key = event['start'].strftime('%Y-%m')
        month_name = event['start'].strftime('%B %Y')
        if month_name not in events_by_month:
            events_by_month[month_name] = []
        events_by_month[month_name].append(event)
    
    for month_name, month_events in events_by_month.items():
        month_text = ""
        for event in month_events:
            days_until = (event['start'].date() - datetime.now().date()).days
            day_indicator = ""
            if days_until == 0:
                day_indicator = " 🚨 **HOY**"
            elif days_until == 1:
                day_indicator = " ⚠️ **MAÑANA**"
            elif days_until <= 7:
                day_indicator = " 🔔"
            
            month_text += f"• **{event['start'].strftime('%d/%m')}** {event['start'].strftime('%H:%M')} - {event['summary']}{day_indicator}\n"
        
        embed.add_field(
            name=f"📅 {month_name}",
            value=month_text,
            inline=False
        )
    
    # Estadísticas rápidas
    today_count = len([e for e in exams_events if e['start'].date() == datetime.now().date()])
    week_count = len([e for e in exams_events if (e['start'].date() - datetime.now().date()).days <= 7])
    
    embed.set_footer(text=f"🔄 Sincronizado | Hoy: {today_count} | Próxima semana: {week_count} | Total: {len(exams_events)}")
    
    await interaction.followup.send(embed=embed)

def setup_command(calendario_group, cog):
    """Configura el comando examenes en el grupo calendario"""
    
    @calendario_group.command(name="examenes", description="Muestra los próximos exámenes")
    async def examenes(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await send_exams_events(interaction, cog.calendar_sync)
