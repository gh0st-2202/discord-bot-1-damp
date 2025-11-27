import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import importlib
import sys
from datetime import datetime
import pytz
import requests
from icalendar import Calendar
from typing import List, Dict
import asyncio

# Grupo de comandos de calendario
calendario_group = app_commands.Group(
    name="calendario", 
    description="Comandos para gestionar y consultar el calendario académico",
    default_permissions=None
)

class CalendarSync:
    def __init__(self):
        self.timezone = pytz.timezone('Europe/Madrid')
        self.events = []
        self.last_sync = None
        self.calendars = {
            'moodle': {
                'url': os.getenv("MOODLE_CALENDAR_URL"),
                'name': "📚 Moodle",
                'color': 0x00ff00,
                'emoji': "📚"
            },
            'google': {
                'url': os.getenv("GOOGLE_CALENDAR_URL"),
                'name': "📅 Google Calendar",
                'color': 0x4285f4,
                'emoji': "📅"
            }
        }
    
    async def sync_events(self) -> List[Dict]:
        """Sincronización con todos los calendarios - CON MANEJO DE ERRORES MEJORADO"""
        from datetime import timedelta
        now = datetime.now()
        if self.last_sync and (now - self.last_sync).total_seconds() < 300:  # 5 minutos de cache
            print(f"🔄 Usando caché (sincronizado hace {(now - self.last_sync).total_seconds():.0f} segundos)")
            return self.events
            
        print("🔄 Sincronizando calendarios...")
        all_events = []
        sync_success = False
        
        for calendar_id, calendar_info in self.calendars.items():
            try:
                print(f"  📥 Descargando {calendar_info['name']}...")
                response = requests.get(calendar_info['url'], timeout=30)
                response.raise_for_status()
                
                calendar_data = Calendar.from_ical(response.content)
                calendar_events = []
                
                for component in calendar_data.walk():
                    if component.name == "VEVENT":
                        event = self._parse_event(component, calendar_id, calendar_info['name'])
                        if event:
                            calendar_events.append(event)
                
                all_events.extend(calendar_events)
                print(f"  ✅ {len(calendar_events)} eventos de {calendar_info['name']}")
                sync_success = True
                
            except Exception as e:
                print(f"  ❌ Error sincronizando {calendar_info['name']}: {e}")
                # Si hay error, usamos eventos existentes de este calendario
                existing_events = [e for e in self.events if e['calendar'] == calendar_id]
                all_events.extend(existing_events)
                print(f"  🔄 Usando {len(existing_events)} eventos en caché para {calendar_info['name']}")
        
        if sync_success or not self.events:
            all_events.sort(key=lambda x: x['start'])
            self.events = all_events
            self.last_sync = now
            print(f"📊 Sincronización completada. Total eventos: {len(self.events)}")
        else:
            print("⚠️  No se pudo sincronizar, usando caché existente")
            
        return self.events
    
    def _parse_event(self, event_component, calendar_id: str, calendar_name: str):
        """Parsea eventos individuales con mejor manejo de errores"""
        try:
            start_dt = event_component.get('dtstart').dt
            end_dt = event_component.get('dtend').dt
            
            # Manejar diferentes tipos de fecha/hora
            if not isinstance(start_dt, datetime):
                return None
                
            if start_dt.tzinfo is None:
                start_dt = self.timezone.localize(start_dt)
            if isinstance(end_dt, datetime) and end_dt.tzinfo is None:
                end_dt = self.timezone.localize(end_dt)
            
            return {
                'summary': str(event_component.get('summary', 'Sin título')),
                'description': str(event_component.get('description', '')),
                'start': start_dt,
                'end': end_dt,
                'location': str(event_component.get('location', '')),
                'url': str(event_component.get('url', '')),
                'uid': str(event_component.get('uid', '')),
                'calendar': calendar_id,
                'calendar_name': calendar_name,
                'color': self.calendars[calendar_id]['color'],
                'emoji': self.calendars[calendar_id]['emoji']
            }
        except Exception as e:
            print(f"⚠️  Error parseando evento: {e}")
            return None

    def get_events_by_calendar(self, calendar_id: str, days: int = 30) -> List[Dict]:
        """Obtiene eventos de un calendario específico"""
        from datetime import timedelta
        now = datetime.now(self.timezone)
        future_date = now + timedelta(days=days)
        
        return [e for e in self.events 
                if e['calendar'] == calendar_id and now <= e['start'] <= future_date]

    def get_events_today(self) -> List[Dict]:
        """Eventos de hoy"""
        today = datetime.now(self.timezone).date()
        return [e for e in self.events if e['start'].date() == today]

    def get_events_next_days(self, days: int) -> List[Dict]:
        """Eventos próximos en N días"""
        from datetime import timedelta
        now = datetime.now(self.timezone)
        future_date = now + timedelta(days=days)
        
        return [e for e in self.events if now <= e['start'] <= future_date]

    def get_future_events(self, after_days: int = 30) -> List[Dict]:
        """Eventos futuros (después de N días)"""
        from datetime import timedelta
        future_date = datetime.now(self.timezone) + timedelta(days=after_days)
        return [e for e in self.events if e['start'] > future_date]

    def get_calendar_stats(self) -> Dict:
        """Obtiene estadísticas del calendario"""
        from datetime import timedelta
        now = datetime.now(self.timezone)
        
        calendar_stats = {}
        for calendar_id in self.calendars:
            calendar_events = [e for e in self.events if e['calendar'] == calendar_id]
            calendar_stats[calendar_id] = {
                'total': len(calendar_events),
                'today': len([e for e in calendar_events if e['start'].date() == now.date()]),
                'next_7_days': len([e for e in calendar_events if now <= e['start'] <= (now + timedelta(days=7))]),
            }
        
        return {
            'total': len(self.events),
            'today': len(self.get_events_today()),
            'next_7_days': len(self.get_events_next_days(7)),
            'next_30_days': len(self.get_events_next_days(30)),
            'future': len(self.get_future_events(30)),
            'last_sync': self.last_sync.strftime('%d/%m/%Y %H:%M') if self.last_sync else "Nunca",
            'calendars': calendar_stats
        }

class CalendarioCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.calendar_sync = CalendarSync()
        self.loaded_commands = []

    async def load_calendario_commands(self):
        """Carga automáticamente todos los comandos de la carpeta calendario"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        calendario_commands_path = os.path.join(current_dir, "calendario")
        
        if not os.path.exists(calendario_commands_path):
            print("❌ No se encuentra la carpeta calendario")
            return

        if calendario_commands_path not in sys.path:
            sys.path.append(calendario_commands_path)

        for filename in os.listdir(calendario_commands_path):
            if filename.endswith(".py") and filename not in ["__init__.py", "calendario.py"]:
                module_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(
                        module_name, 
                        os.path.join(calendario_commands_path, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'setup_command'):
                        module.setup_command(calendario_group, self)
                        self.loaded_commands.append(module_name)
                        print(f"✅ Comando calendario cargado: {module_name}")
                    else:
                        print(f"⚠️  Módulo {module_name} no tiene función setup_command")
                        
                except Exception as e:
                    print(f"❌ Error al cargar {filename}: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Cuando el cog está listo - Sincronización inicial"""
        print("🔄 Iniciando sincronización inicial de calendarios...")
        await self.calendar_sync.sync_events()

    async def cog_load(self):
        """Cuando el cog se carga"""
        await self.load_calendario_commands()

    async def ensure_sync(self):
        """Asegura que los calendarios estén sincronizados antes de usar comandos"""
        if not self.calendar_sync.events or not self.calendar_sync.last_sync:
            await self.calendar_sync.sync_events()

async def setup(bot):
    bot.tree.add_command(calendario_group)
    calendario_cog = CalendarioCog(bot)
    await bot.add_cog(calendario_cog)
