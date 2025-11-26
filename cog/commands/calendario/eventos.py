import discord
from discord import app_commands
from datetime import datetime, timedelta

async def send_events_embed(interaction: discord.Interaction, calendar_sync):
    """Envía un embed completo con todos los eventos categorizados"""
    calendar = calendar_sync
    # Asegurar sincronización antes de mostrar eventos
    await calendar.sync_events()
    
    # Obtener eventos
    today_events = calendar.get_events_today()
    week_events = calendar.get_events_next_days(7)
    month_events = calendar.get_events_next_days(30)
    future_events = calendar.get_future_events(30)
    stats = calendar.get_calendar_stats()
    
    # Crear embed principal
    embed = discord.Embed(
        title="📅 Calendario - 1º GS DAMP",
        color=0x7289da,
        timestamp=datetime.now()
    )
    
    embed.set_footer(text=f"🔄 Sincronizado | Última actualización: {stats['last_sync']}")
    
    # Hoy
    if today_events:
        today_text = ""
        for event in today_events[:8]:
            emoji = "📚" if event['calendar'] == 'moodle' else "📝"
            today_text += f"{emoji} **{event['start'].strftime('%H:%M')}** - {event['summary']}\n"
        if len(today_events) > 8:
            today_text += f"*... y {len(today_events) - 8} más*"
    else:
        today_text = "✅ No hay eventos para hoy"
    
    embed.add_field(
        name=f"📌 Hoy ({len(today_events)})",
        value=today_text,
        inline=False
    )
    
    # Próximos 7 días
    week_events_filtered = [e for e in week_events if e not in today_events]
    if week_events_filtered:
        week_text = ""
        for event in week_events_filtered[:6]:
            emoji = "📚" if event['calendar'] == 'moodle' else "📝"
            week_text += f"{emoji} **{event['start'].strftime('%a %d/%m %H:%M')}** - {event['summary']}\n"
        if len(week_events_filtered) > 6:
            week_text += f"*... y {len(week_events_filtered) - 6} más*"
    else:
        week_text = "✅ No hay eventos esta semana"
    
    embed.add_field(
        name=f"🔔 Próximos 7 días ({len(week_events_filtered)})",
        value=week_text,
        inline=False
    )
    
    # Próximos 30 días
    month_events_filtered = [e for e in month_events if e not in week_events]
    if month_events_filtered:
        month_text = ""
        for event in month_events_filtered[:5]:
            emoji = "📚" if event['calendar'] == 'moodle' else "📝"
            month_text += f"{emoji} **{event['start'].strftime('%d/%m')}** - {event['summary']}\n"
        if len(month_events_filtered) > 5:
            month_text += f"*... y {len(month_events_filtered) - 5} más*"
    else:
        month_text = "✅ No hay eventos este mes"
    
    embed.add_field(
        name=f"📈 Próximos 30 días ({len(month_events_filtered)})",
        value=month_text,
        inline=False
    )
    
    # Futuros
    if future_events:
        future_text = f"📊 **Total eventos futuros:** {len(future_events)}"
        for event in future_events[:2]:
            emoji = "📚" if event['calendar'] == 'moodle' else "📝"
            future_text += f"\n{emoji} **{event['start'].strftime('%d/%m/%Y')}** - {event['summary']}"
        if len(future_events) > 2:
            future_text += f"\n*... y {len(future_events) - 2} más*"
    else:
        future_text = "✅ No hay eventos futuros programados"
    
    embed.add_field(
        name=f"\n🚀 Eventos Futuros ({len(future_events)})",
        value=future_text,
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

def setup_command(calendario_group, cog):
    """Configura el comando eventos en el grupo calendario"""
    
    @calendario_group.command(name="eventos", description="Muestra los eventos de todos los calendarios")
    async def eventos(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await send_events_embed(interaction, cog.calendar_sync)
