# 🚆 Bot de Telegram para Gestión de Preferencias de Billetes Renfe

Este bot de Telegram permite a los usuarios registrar sus preferencias de viaje (origen, destino y fecha) y gestionar esas 
solicitudes para recibir notificaciones cuando los billetes estén disponibles.  

> **Nota:** Este bot **no realiza la búsqueda automática de billetes en la web de Renfe**, sino que sirve para gestionar y
            almacenar las preferencias de viaje, facilitando la notificación cuando se integre una fuente real de disponibilidad.

# 🖥️ Ejecución en servidor o plataforma online
Este bot está diseñado para funcionar de forma continua en un servidor o en una plataforma online que soporte Python, como por 
ejemplo:

Replit: Puedes subir el código y configurar las variables de entorno en la sección "Secrets". Replit permite que el bot se mantenga 
activo 24/7 sin interrupciones.
Servidores VPS o cloud (DigitalOcean, AWS, Heroku, etc.): Puedes desplegar el bot en un servidor Linux, asegurándote de instalar 
Python, configurar las variables de entorno y ejecutar el script con screen o tmux para que corra en segundo plano.

El bot utiliza un loop asíncrono para mantener la conexión con Telegram y gestionar comandos, por lo que es importante que el entorno donde se ejecuta esté siempre encendido y conectado a Internet.

## ✨ Funcionalidades

- ✅ Guardar preferencias de viaje (origen, destino, fecha) vía Telegram  
- 📋 Visualizar solicitudes guardadas  
- 🗑 Eliminar solicitudes  
- 🔄 Tarea periódica que puede usarse para enviar notificaciones (requiere implementación externa de comprobación de disponibilidad)

## 📦 Tecnologías utilizadas

- Python 3  
- PostgreSQL (vía `asyncpg`)  
- Telegram Bot API (usando `python-telegram-bot`)  
- Asynchronous I/O (`asyncio`)  
- Logging local y remoto  

## ⚙️ Configuración

Antes de ejecutar el bot, necesitas configurar las siguientes **variables de entorno**:

```bash
BOT_TOKEN=tu_token_de_telegram
DATABASE_URL=postgresql://usuario:contraseña@host:puerto/nombre_db
