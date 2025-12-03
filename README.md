# 🤖 Discord Bot v5 - Modern Economy & Games

**Una potente plataforma de economía y entretenimiento para Discord con base de datos en tiempo real**

---

## 🎯 **Características Principales**

### 💰 **Sistema de Economía Completo**
- **Saldo personal** - Revisa tus monedas virtuales
- **Transferencias entre usuarios** - Envía dinero a amigos
- **Recompensas diarias** - Bonificación por conexión diaria
- **Leaderboard en vivo** - Actualización automática de posiciones

### 🎮 **Juegos Integrados**
- **Blackjack** - Clásico juego de cartas
- **Wordless** - Adivinanza de palabras por pistas
- *¡Más juegos en desarrollo!*

### 📅 **Calendario Inteligente**
- Sincronización automática con calendarios externos
- Configurable mediante variables de entorno
- Visualización directa en Discord

### 🤖 **Funciones de IA**
- Asistente inteligente integrado
- Respuestas contextuales y útiles

### ⚡ **Utilidades Técnicas**
- **Arquitectura modular** - Cada comando es independiente
- **Base de datos en tiempo real** con Supabase
- **Comandos de administración** avanzados

---

## 🛠️ **Configuración Rápida**

### Prerrequisitos
```
- Node.js 16+
- Cuenta de Discord Developer
- Cuenta en Supabase (gratuita)
- Tokens de calendario (opcional)
```

### Instalación
```bash
# Clonar repositorio
git clone [url-del-repositorio]

# Instalar dependencias
npm install

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Iniciar el bot
npm start
```

### Variables de Entorno Críticas
```env
DISCORD_TOKEN=tu_token_aqui
SUPABASE_URL=tu_url_supabase
SUPABASE_KEY=tu_clave_supabase
CALENDAR_LINKS=enlaces_calendario
```

---

## 📁 **Estructura del Proyecto**
```
📦 bot-discord-v5
├── 📂 commands/          # Comandos modulares
│   ├── economia/        # Sistema económico
│   ├── juegos/          # Juegos (estructura especial)
│   ├── calendario/      # Gestión de calendario
│   └── utilidades/      # Comandos varios
├── 📂 database/         # Configuración Supabase
├── 📂 assets/           # Recursos e imágenes
├── .env                 # Configuración sensible
├── README.md           # Este archivo
└── package.json        # Dependencias
```

---

## 🎮 **Uso de Comandos**

### Comandos Básicos
```
!ping          - Verificar latencia del bot
!saldo         - Consultar balance actual
!daily         - Reclamar recompensa diaria
!transferir @usuario cantidad - Enviar dinero
```

### Sistema de Juegos
```
!blackjack apuesta    - Iniciar juego de blackjack
!wordless             - Jugar adivinanza de palabras
```

### Herramientas de Administración
```
!leaderboard          - Tabla de clasificación
!sincronizar          - Sincronizar datos
!give @usuario cantidad - Otorgar monedas (admin)
```

---

## 🚀 **Roadmap v5-final** (Próximas Funciones)

### 🔄 **En Desarrollo**
- [ ] **Sistema de Criptomonedas** - Economía virtual avanzada
- [ ] **Inventarios Personalizados** - Almacenamiento de objetos

### 📋 **Próximamente**
- [ ] **Objetos con Imágenes Locales** - Assets visuales
- [ ] **Base de Datos Mejorada** - Optimización para nuevos features
- [ ] **Tienda Local** - Comercio entre usuarios
- [ ] **Juego de Rol por Opciones** - Aventuras con imágenes aleatorias

---

## 🏆 **Leaderboard en Vivo**
El sistema actualiza automáticamente las posiciones con cada transacción. ¡Compite con tus amigos por el primer lugar!

---

## 🤝 **Contribuir**

### Reportar Problemas
1. Revisa si el problema ya existe en los issues
2. Crea un nuevo issue con detalles específicos
3. Incluye pasos para reproducir el error

### Sugerir Mejoras
¡Las ideas nuevas son bienvenidas! Abre un issue con la etiqueta `enhancement`.

---

## 📞 **Soporte y Contacto**

### Solución de Problemas Comunes
- **Bot no responde**: Verifica los permisos del bot en Discord
- **Error de base de datos**: Confirma las credenciales de Supabase
- **Comandos no registrados**: Revisa los intents en Discord Developer Portal

### Enlaces Útiles
- [Documentación de Discord.js](https://discord.js.org/)
- [Portal de Desarrollo de Discord](https://discord.com/developers)
- [Documentación de Supabase](https://supabase.com/docs)

---

## 📜 **Licencia**
Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

---

## ✨ **Agradecimientos**
- **Discord.js** por la excelente librería
- **Supabase** por la base de datos en tiempo real
- **Comunidad de desarrolladores** por el apoyo constante

---

**⭐ ¿Te gusta este proyecto? ¡Dale una estrella en GitHub!**

*Última actualización: Diciembre 2023 - Versión 5.0*
