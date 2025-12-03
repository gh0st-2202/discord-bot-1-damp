# 🤖 Clase Bot v5 - Tu Asistente de Discord Inteligente

**Un bot multifunción para gestión académica, economía virtual y entretenimiento**

---

## 📋 **Índice**
- [🚀 Características Principales](#-características-principales)
- [⚡ Comandos Rápidos](#-comandos-rápidos)
- [📅 Sistema de Calendario](#-sistema-de-calendario)
- [💰 Economía Virtual](#-economía-virtual)
- [🤖 Asistente de IA](#-asistente-de-ia)
- [🎮 Juegos Integrados](#-juegos-integrados)
- [🔧 Instalación](#-instalación)
- [⚙️ Configuración](#-configuración)
- [🏗️ Estructura del Proyecto](#️-estructura-del-proyecto)

---

## 🚀 **Características Principales**

| Característica | Descripción | Estado |
|----------------|-------------|---------|
| **📅 Calendario Multiplataforma** | Sincronización automática con Google y Moodle | ✅ **Activo** |
| **💰 Sistema Económico** | Monedas virtuales, transferencias y robos | ✅ **Activo** |
| **🎮 Juegos Interactivos** | Blackjack y Wordless integrados | ✅ **Activo** |
| **🤖 Asistente de IA** | Integración con modelos avanzados vía OpenRouter | ✅ **Activo** |
| **🏆 Leaderboard en Vivo** | Clasificación actualizada automáticamente | ✅ **Activo** |
| **⚡ Arquitectura Modular** | Cada comando es independiente y escalable | ✅ **Activo** |

---

## ⚡ **Comandos Rápidos**

### **Comandos Generales**
| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/ping` | Comprueba la conectividad con el bot | `/ping` |
| `/sudo` | Panel de administración (solo admins) | `/sudo` |

---

## 📅 **Sistema de Calendario**

Conecta múltiples fuentes para una gestión académica completa:

```bash
/calendario buscar <término>
# Busca eventos en Google y Moodle
# Ejemplo: /calendario buscar "examen matemáticas"

/calendario eventos
# Muestra todos los eventos futuros sincronizados

/calendario examenes
# Lista los próximos exámenes desde Google Calendar

/calendario hoy
# Tareas y exámenes programados para hoy

/calendario tareas
# Plazos de entrega próximos desde Moodle
```

**🔗 Fuentes Soportadas:**
- ✅ Google Calendar (eventos y exámenes)
- ✅ Moodle/Canvas (tareas y plazos)

---

## 💰 **Economía Virtual**

Sistema económico completo con interacciones sociales:

### **Gestión de Saldo**
```bash
/economy saldo [@usuario]
# Ver tu saldo o el de otro usuario
# Ejemplo: /economy saldo @usuario

/economy transferir <@destinatario> <cantidad>
# Envía dinero a otro usuario
# Ejemplo: /economy transferir @amigo 500

/economy diario
# Reclama tu recompensa diaria
```

### **Interacciones de Riesgo** ⚠️
```bash
/economy robar <@víctima>
# Intenta robar dinero a otro usuario
# ¡Puedes ser capturado y multado!
```

### **Características del Sistema:**
- 💸 **Transferencias instantáneas**
- 🎁 **Recompensas diarias progresivas**
- 🚨 **Sistema anti-abuso integrado**
- 📊 **Leaderboard automático**

---

## 🤖 **Asistente de IA**

Conectado a modelos avanzados a través de OpenRouter:

```bash
/ia <mensaje> [modelo]
# Chatea con la IA (modelo opcional)

# Ejemplos:
/ia ¿Cómo resolver esta ecuación?
/ia Explícame la fotosíntesis model:gpt-4
```

---

## 🎮 **Juegos Integrados**

### **🎲 BlackJack - Casino Virtual**
```bash
# 1. Crear partida
/blackjack crear <apuesta_mínima>
# Ejemplo: /blackjack crear 50

# 2. Unirse a partida
/blackjack unirse <apuesta>
# Ejemplo: /blackjack unirse 100

# Apuesta debe ser ≥ apuesta mínima
# Múltiples jugadores pueden unirse
```

### **🔤 Wordless - Adivina la Palabra**
```bash
# 1. Iniciar juego
/wordless crear
# El bot elige una palabra secreta

# 2. Hacer intentos
/wordless intento <palabra>
# Ejemplo: /wordless intento "casa"

# Sistema de pistas por letras
# Límite de intentos configurable
```

---

## 🔧 **Instalación**

### **Requisitos Previos**
- 🐍 **Python 3.8+**
- 🚀 **Cuenta en [Supabase](https://supabase.com)**
- 🔑 **API Key de [OpenRouter](https://openrouter.ai)**
- 🤖 **Bot de Discord configurado**

### **Pasos de Instalación**
```bash
# 1. Clonar repositorio
git clone https://github.com/tuusuario/clase-bot.git
cd clase-bot

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar variables (ver sección siguiente)
# 6. Ejecutar bot
python main-bot.py
```

---

## ⚙️ **Configuración**

### **Archivo `.env`**
```env
# Discord
DISCORD_TOKEN=tu_token_aqui
CHANNEL_LEADERBOARD_ID=id_canal_leaderboard
CHANNEL_TROPHY_ID=id_canal_ganadores
CHANNEL_BET_ID=id_canal_apuestas

# Inteligencia Artificial
OPENROUTER_API_KEY=tu_clave_openrouter

# Calendarios
MOODLE_CALENDAR_URL=https://tumoodle.com/feed
GOOGLE_CALENDAR_URL=https://calendar.google.com/ical/...

# Base de Datos
SUPABASE_URL=https://tuid.supabase.co
SUPABASE_KEY=tu_clave_supabase
```

### **Configuración en Discord Developer Portal**
1. Activar **Privileged Gateway Intents**:
   - ✅ PRESENCE INTENT
   - ✅ SERVER MEMBERS INTENT
   - ✅ MESSAGE CONTENT INTENT
2. Añadir permisos de bot:
   - ✅ Read Messages
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Use Slash Commands

---

## 🏗️ **Estructura del Proyecto**

```
Clase-Bot_v5/
├── 📁 cog/                    # Extensiones modulares
│   ├── 📁 commands/          # Comandos principales
│   │   ├── 📁 calendario/    # Sistema completo de calendario
│   │   │   ├── buscar.py     # 🔍 Búsqueda de eventos
│   │   │   ├── eventos.py    # 📋 Lista de eventos
│   │   │   ├── examenes.py   # 📝 Próximos exámenes
│   │   │   ├── hoy.py        # 📅 Eventos de hoy
│   │   │   └── tareas.py     # ✅ Plazos de tareas
│   │   ├── ping.py          # 🏓 Comando de conectividad
│   │   └── 📁 sudo/         # 👑 Comandos de administración
│   │       ├── 📁 commands/
│   │       │   └── sincronizar.py  # 🔄 Sincronización manual
│   │       └── 📁 economy/
│   │           ├── give.py          # 💸 Otorgar dinero
│   │           └── leaderboard.py   # 🏆 Tabla de clasificación
│   ├── 📁 economia/          # 💰 Sistema económico
│   │   ├── 📁 economy/
│   │   │   ├── daily.py     # 🎁 Recompensa diaria
│   │   │   ├── robos.py     # 🦹 Robos entre usuarios
│   │   │   ├── saldo.py     # 💳 Consultar saldo
│   │   │   └── transferir.py # 🔄 Transferencias
│   │   └── economy.py       # 🔌 Cog principal de economía
│   ├── 📁 ia/               # 🤖 Inteligencia Artificial
│   │   └── ia.py           # 💬 Interacción con modelos
│   └── 📁 juegos/           # 🎮 Sistema de juegos
│       ├── blackjack.py    # 🎲 Juego de blackjack
│       └── wordless.py     # 🔤 Juego de adivinanza
├── main-bot.py             # 🚀 Punto de entrada principal
├── requirements.txt        # 📦 Dependencias de Python
├── render.yaml            # ☁️ Configuración de despliegue
└── README.md              # 📖 Este archivo
```

---

## 🔮 **Roadmap v5-final**

### **🚧 En Desarrollo Inmediato**
- [ ] **Criptomonedas Virtuales** 📈
  - Sistema de trading básico
  - Fluctuación de precios simulada
  - Mercado de intercambio P2P

---

## 🛠️ **Tecnologías Utilizadas**

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **discord.py** | 2.3+ | Interacción con Discord API |
| **Supabase** | Latest | Base de datos en tiempo real |
| **OpenRouter API** | - | Acceso a modelos de IA |
| **ics.py** | Latest | Parseo de calendarios iCal |
| **requests** | 2.31+ | Comunicación HTTP |
| **python-dotenv** | Latest | Gestión de variables de entorno |

---

## 🤝 **Contribuir al Proyecto**

### **Reportar Problemas**
1. Verifica si el problema ya existe en los **Issues**
2. Crea un nuevo issue con:
   - Descripción clara del problema
   - Pasos para reproducirlo
   - Capturas de pantalla (si aplica)
   - Logs de error (si existen)

### **Sugerir Mejoras**
¡Las nuevas ideas son bienvenidas! Usa la plantilla de **Feature Request** e incluye:
- Descripción detallada de la funcionalidad
- Casos de uso concretos
- Beneficios para la comunidad

### **Desarrollo Local**
```bash
# 1. Fork el repositorio
# 2. Clona tu fork localmente
# 3. Crea una rama para tu feature
git checkout -b mi-nueva-feature
# 4. Realiza tus cambios
# 5. Haz commit y push
# 6. Abre un Pull Request
```

---

## ❓ **Preguntas Frecuentes**

### **¿Cómo sincronizo mi calendario?**
1. Obtén la URL pública de tu calendario de Google/Moodle
2. Añádela al archivo `.env`
3. Usa `/sudo sincronizar` para forzar una sincronización

### **¿Por qué no funcionan los comandos?**
- Verifica que el bot tenga los permisos necesarios
- Asegúrate de usar la barra diagonal (`/`) al inicio
- Comprueba que el bot esté en línea con `/ping`

### **¿Cómo obtener una API Key de OpenRouter?**
1. Regístrate en [openrouter.ai](https://openrouter.ai)
2. Ve a "API Keys" en tu dashboard
3. Crea una nueva key y cópiala al `.env`

---

## ✨ **Agradecimientos**

Un especial agradecimiento a:

| Proyecto | Contribución |
|----------|--------------|
| **Discord.py** | Excelente librería para Python |
| **Supabase** | Base de datos gratuita y potente |
| **OpenRouter** | Acceso unificado a modelos de IA |
| **Comunidad** | Por las pruebas y sugerencias |

---

**⭐ ¡Dale una estrella al repositorio si te gusta el proyecto!**

*Última actualización: 3 Diciembre 2025 • Versión 5.0*
