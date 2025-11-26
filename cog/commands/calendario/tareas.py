import discord
from discord import app_commands
from datetime import datetime, timedelta

async def send_tasks_events(interaction: discord.Interaction, calendar_sync):
    """Muestra solo los eventos de Moodle (tareas)"""
    calendar = calendar_sync
    # Asegurar sincronización antes de mostrar eventos
    await calendar.sync_events()
    
    tasks_events = calendar.get_events_by_calendar('moodle', days=30)
    
    if not tasks_events:
        embed = discord.Embed(
            title="📚 Tareas",
            description="✅ No hay tareas pendientes en los próximos 30 días",
            color=0x00ff00
        )
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="📚 Tareas",
        description=f"**{len(tasks_events)}** tareas encontradas",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    # Agrupar por semana
    events_by_week = {}
    for event in tasks_events:
        week_start = event['start'].date() - timedelta(days=event['start'].weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        week_name = f"Semana {week_start.strftime('%d/%m')}"
        if week_name not in events_by_week:
            events_by_week[week_name] = []
        events_by_week[week_name].append(event)
    
    for week_name, week_events in list(events_by_week.items())[:6]:
        week_text = ""
        for event in week_events:
            days_until = (event['start'].date() - datetime.now().date()).days
            urgency = ""
            if days_until == 0:
                urgency = " 🚨 **HOY**"
            elif days_until == 1:
                urgency = " ⚠️ **MAÑANA**"
            elif days_until <= 3:
                urgency = " 🔔"
            
            week_text += f"• **{event['start'].strftime('%a %d/%m')}** {event['start'].strftime('%H:%M')} - {event['summary']}{urgency}\n"
        
        embed.add_field(
            name=f"📅 {week_name}",
            value=week_text,
            inline=False
        )
    
    # Estadísticas rápidas
    today_count = len([e for e in tasks_events if e['start'].date() == datetime.now().date()])
    urgent_count = len([e for e in tasks_events if (e['start'].date() - datetime.now().date()).days <= 3])
    
    embed.set_footer(text=f"🔄 Sincronizado | Hoy: {today_count} | Urgentes (≤3 días): {urgent_count} | Total: {len(tasks_events)}")
    
    await interaction.followup.send(embed=embed)

def setup_command(calendario_group, cog):
    """Configura el comando tareas en el grupo calendario"""
    
    @calendario_group.command(name="tareas", description="Muestra las próximas tareas")
    async def tareas(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await send_tasks_events(interaction, cog.calendar_sync)
