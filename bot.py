import nest_asyncio
nest_asyncio.apply()

import os
import json  # (Ya no se usa para persistir datos, pero puede ser útil para debug)
import asyncio
import logging
from datetime import datetime
import asyncpg  # Para conexión asíncrona a PostgreSQL
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackContext
)

# Token del bot (se debe configurar en las variables de entorno)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8088144724:AAEAhC1CZbq6Dtd_hJEZoNdKml58z0h0vlM")

# Estados del flujo de conversación
SET_ORIGEN, SET_DESTINO, SET_FECHA, DELETE_REQUEST = range(4)

# Definir la ruta del script antes de usarla
script_dir = os.path.dirname(os.path.abspath(__file__))

# Crear el directorio logs si no existe
log_dir = os.path.join(script_dir, 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# --- Configuración de logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(script_dir, 'logs/renfe_search.log'))
    ]
)
logger = logging.getLogger(__name__)

# Variable global para el pool de conexiones a la base de datos
DB_POOL = None



# ----------------- Funciones para la Base de Datos ----------------- #
async def init_db():
    """Inicializa la conexión a la base de datos y crea la tabla si no existe."""
    global DB_POOL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise Exception("DATABASE_URL no está configurada")
    DB_POOL = await asyncpg.create_pool(dsn=db_url)
    async with DB_POOL.acquire() as connection:
        await connection.execute(''' 
            CREATE TABLE IF NOT EXISTS user_preferences (
                id SERIAL PRIMARY KEY,
                chat_id TEXT NOT NULL,
                origen TEXT NOT NULL,
                destino TEXT NOT NULL,
                fecha DATE NOT NULL
            );
        ''')

        await connection.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                chat_id TEXT NOT NULL,
                origen TEXT NOT NULL,
                destino TEXT NOT NULL,
                fecha DATE NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notificacion_enviada BOOLEAN DEFAULT false  -- Agregamos la columna
            );
        ''')

async def add_preference_db(chat_id: str, origen: str, destino: str, fecha: datetime.date) -> bool:
    """Inserta una nueva preferencia de viaje en la base de datos."""
    try:
        async with DB_POOL.acquire() as connection:
            await connection.execute('''
                INSERT INTO user_preferences (chat_id, origen, destino, fecha)
                VALUES ($1, $2, $3, $4)
            ''', chat_id, origen, destino, fecha)
        return True
    except Exception as e:
        print(f"Error al insertar la preferencia: {e}")
        return False

async def get_preferences_db(chat_id: str) -> list:
    """Recupera las preferencias de viaje para un chat_id dado."""
    try:
        async with DB_POOL.acquire() as connection:
            rows = await connection.fetch('''
                SELECT id, origen, destino, fecha FROM user_preferences
                WHERE chat_id = $1 ORDER BY id
            ''', chat_id)
            # Convertir la fecha al formato dd/mm/aaaa para mostrar
            return [
                {
                    "id": row["id"],
                    "origen": row["origen"],
                    "destino": row["destino"],
                    "fecha": row["fecha"].strftime("%d/%m/%Y")
                }
                for row in rows
            ]
    except Exception as e:
        print(f"Error al obtener las preferencias: {e}")
        return []

async def delete_preference_db(chat_id: str, index: int) -> bool:
    """
    Elimina la preferencia de viaje según el índice (orden ascendente por id)
    que se muestra al usuario.
    """
    try:
        preferences = await get_preferences_db(chat_id)
        if index < 0 or index >= len(preferences):
            return False
        pref_id = preferences[index]["id"]
        async with DB_POOL.acquire() as connection:
            await connection.execute('''
                DELETE FROM user_preferences WHERE id = $1 AND chat_id = $2
            ''', pref_id, chat_id)
        return True
    except Exception as e:
        print(f"Error al eliminar la preferencia: {e}")
        return False

# ----------------- Funciones del Bot ----------------- #
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "¡Bienvenido al Bot de Notificaciones!\n"
        "Este bot te avisará tan pronto como los billetes para tu viaje estén disponibles.\n\n"
        "🔹 Usa /set para configurar los detalles de tu viaje (origen, destino y fecha).\n"
        "🔹 Usa /view para ver todas tus solicitudes pendientes.\n"
        "🔹 Usa /delete para eliminar las solicitudes que ya no te interesen."
    )

# --- Flujo para /set ---
async def set_preferences(update: Update, context: CallbackContext):
    await update.message.reply_text("Por favor, introduce el origen:")
    return SET_ORIGEN

async def set_origen(update: Update, context: CallbackContext):
    context.user_data['origen'] = update.message.text
    await update.message.reply_text("Origen guardado. Ahora, introduce el destino:")
    return SET_DESTINO

async def set_destino(update: Update, context: CallbackContext):
    context.user_data['destino'] = update.message.text
    await update.message.reply_text("Destino guardado. Introduce la fecha en formato dd/mm/aaaa:")
    return SET_FECHA

async def set_fecha(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    fecha_text = update.message.text
    try:
        fecha_obj = datetime.strptime(fecha_text, "%d/%m/%Y")
        hoy = datetime.now()
        if fecha_obj.date() < hoy.date():
            await update.message.reply_text("⚠️ La fecha ingresada ya ha pasado. Introduce una fecha futura en formato dd/mm/aaaa:")
            return SET_FECHA

        # Inserta la preferencia en la base de datos
        success = await add_preference_db(
            chat_id,
            context.user_data['origen'],
            context.user_data['destino'],
            fecha_obj.date()
        )
        if success:
            await update.message.reply_text("✅ ¡Datos del viaje guardados correctamente! Recibirás una notificación cuando los billetes estén disponibles.")
            await update.message.reply_text(
                "🔹 ¿Qué quieres hacer ahora?\n"
                "✅ Definir otro viaje: /set\n"
                "📋 Ver solicitudes pendientes: /view\n"
                "🗑 Eliminar una solicitud: /delete"
            )
            # Imprimir para verificación (opcional)
            prefs = await get_preferences_db(chat_id)
            print(f"Datos guardados para {chat_id}: {prefs}")
        else:
            await update.message.reply_text("❌ Error al guardar los datos. Intenta nuevamente.")
            return SET_FECHA
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Fecha inválida. Introduce una fecha en formato *dd/mm/aaaa*:")
        return SET_FECHA

# --- Comando /view ---
async def view_requests(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    prefs = await get_preferences_db(chat_id)
    if not prefs:
        await update.message.reply_text("No tienes solicitudes pendientes.")
        return
    messages = ["📋 Solicitudes pendientes:"]
    for idx, req in enumerate(prefs, start=1):
        messages.append(f"{idx}. Origen: {req['origen']} → Destino: {req['destino']} | Fecha: {req['fecha']}")
    await update.message.reply_text("\n".join(messages))

# --- Flujo para /delete ---
async def delete_request(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    prefs = await get_preferences_db(chat_id)
    if not prefs:
        await update.message.reply_text("No tienes solicitudes para eliminar.")
        return ConversationHandler.END
    messages = ["🗑 Selecciona el número de la solicitud que deseas eliminar:"]
    for idx, req in enumerate(prefs, start=1):
        messages.append(f"{idx}. Origen: {req['origen']} → Destino: {req['destino']} | Fecha: {req['fecha']}")
    await update.message.reply_text("\n".join(messages))
    return DELETE_REQUEST

async def delete_request_confirm(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    try:
        index = int(update.message.text) - 1
        success = await delete_preference_db(chat_id, index)
        if success:
            await update.message.reply_text("✅ Solicitud eliminada correctamente.")
        else:
            await update.message.reply_text("❌ Número de solicitud inválido. Inténtalo de nuevo.")
            return DELETE_REQUEST
    except ValueError:
        await update.message.reply_text("⚠️ Por favor, introduce un número válido.")
        return DELETE_REQUEST
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("❌ Operación cancelada.")
    return ConversationHandler.END

# ----------------- Función para enviar notificaciones ----------------- #
async def send_notifications():
    """Consulta la base de datos y envía notificaciones a los usuarios."""
    try:
        async with DB_POOL.acquire() as connection:
            # Recupera las notificaciones pendientes (notificacion_enviada = false)
            notifications = await connection.fetch('''
                SELECT chat_id, message
                FROM notifications
                WHERE notificacion_enviada = false  -- Aseguramos que no se ha enviado una notificación
            ''')

            # Enviar una notificación a cada usuario
            for notification in notifications:
                chat_id = notification['chat_id']
                message = notification['message']

                # Enviar el mensaje al usuario
                await application.bot.send_message(chat_id=chat_id, text=message)

                # Marcar la notificación como enviada en la base de datos
                await connection.execute('''
                    UPDATE notifications
                    SET notificacion_enviada = true
                    WHERE chat_id = $1 AND message = $2
                ''', chat_id, message)
        
    except Exception as e:
        logger.error(f"Error al enviar notificaciones: {e}")


# ----------------- Función de comprobación periódica ----------------- #
async def periodic_check():
    """Función para comprobar nuevas notificaciones cada intervalo de tiempo."""
    while True:
        await send_notifications()  # Enviar notificaciones
        await asyncio.sleep(30)  # Esperar 30 segundos antes de la siguiente comprobación



# ----------------- Función principal asíncrona ----------------- #
async def main():
    try:
        # Inicializa la base de datos
        await init_db()

        # Configuración del bot
        application = Application.builder().token(BOT_TOKEN).build()

        # Configura los manejadores de conversación
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('set', set_preferences)],
            states={
                SET_ORIGEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_origen)],
                SET_DESTINO: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_destino)],
                SET_FECHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_fecha)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        delete_handler = ConversationHandler(
            entry_points=[CommandHandler("delete", delete_request)],
            states={DELETE_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_request_confirm)]},
            fallbacks=[CommandHandler("cancel", cancel)]
        )

        # Agrega los handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("view", view_requests))
        application.add_handler(conv_handler)
        application.add_handler(delete_handler)

        logger.info("🤖 Bot en ejecución...")

        # Elimina cualquier webhook activo antes de iniciar el polling
        await application.bot.delete_webhook()
        
        asyncio.create_task(periodic_check())  # Inicia la comprobación periódica de notificaciones  
        
        # Inicia el polling (esto bloquea hasta que el bot se detenga)
        await application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        import traceback
        logger.error(f"Error en el bot: {e}\n{traceback.format_exc()}")



if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
