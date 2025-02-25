import json
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackContext
)

USERS_PREF_FILE = 'user_preferences.json'
BOT_TOKEN = '8088144724:AAEAhC1CZbq6Dtd_hJEZoNdKml58z0h0vlM'

# Estados del flujo de conversación
SET_ORIGEN, SET_DESTINO, SET_FECHA, DELETE_REQUEST = range(4)

def load_preferences():
    """Load preferences with additional error handling"""
    try:
        with open(USERS_PREF_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding preferences: {e}")
        return {}
    except Exception as e:
        print(f"Error loading preferences: {e}")
        return {}

def save_preferences(prefs):
    """Save preferences with additional error handling"""
    try:
        with open(USERS_PREF_FILE, 'w') as f:
            json.dump(prefs, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving preferences: {e}")
        return False

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "¡Bienvenido al Bot de Notificaciones!\n"
        "Este bot te avisará tan pronto como los billetes para tu viaje estén disponibles.\n\n"
        "🔹 Usa /set para configurar los detalles de tu viaje (origen, destino y fecha).\n"
        "🔹 Usa /view para ver todas tus solicitudes pendientes.\n"
        "🔹 Usa /delete para eliminar las solicitudes que ya no te interesen."
    )

async def set_preferences(update: Update, context: CallbackContext):
    await update.message.reply_text("Por favor, introduce el origen:")
    return SET_ORIGEN

async def set_origen(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    prefs = load_preferences()

    if chat_id not in prefs:
        prefs[chat_id] = []  # Inicializar la lista de preferencias si no existe
    save_preferences(prefs)

    context.user_data['origen'] = update.message.text
    await update.message.reply_text("Origen guardado. Ahora, introduce el destino:")
    return SET_DESTINO

async def set_destino(update: Update, context: CallbackContext):
    context.user_data['destino'] = update.message.text
    await update.message.reply_text("Destino guardado. Introduce la fecha en formato dd/mm/aaaa:")
    return SET_FECHA

async def set_fecha(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    prefs = load_preferences()

    fecha_text = update.message.text
    try:
        fecha_obj = datetime.strptime(fecha_text, "%d/%m/%Y")

        # Verify if the date is in the past
        hoy = datetime.now()
        if fecha_obj.date() < hoy.date():
            await update.message.reply_text("⚠️ La fecha ingresada ya ha pasado. Introduce una fecha futura en formato dd/mm/aaaa:")
            return SET_FECHA  # Ask for the date again

        if chat_id not in prefs:
            prefs[chat_id] = []

        nueva_preferencia = {
            'origen': context.user_data['origen'],
            'destino': context.user_data['destino'],
            'fecha': fecha_obj.strftime("%d/%m/%Y")
        }

        # Add logging to verify the data before saving
        print(f"Saving new preference: {nueva_preferencia}")

        # Ensure we're appending to the list
        if not isinstance(prefs[chat_id], list):
            prefs[chat_id] = []
        prefs[chat_id].append(nueva_preferencia)

        # Save preferences and verify
        saved = save_preferences(prefs)
        if saved:
            await update.message.reply_text("✅ ¡Datos del viaje guardados correctamente! Cuando los billetes estén disponibles para la venta te notificaré.")
            # Verify saved data
            verification = load_preferences()
            print(f"Verified saved data for {chat_id}: {verification.get(chat_id, [])}")
        else:
            await update.message.reply_text("❌ Error al guardar los datos de viaje. Por favor, intenta nuevamente.")
            return SET_FECHA

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Fecha inválida. Introduce una fecha en formato *dd/mm/aaaa*:")
        return SET_FECHA

async def view_requests(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    prefs = load_preferences()

    if chat_id not in prefs or not prefs[chat_id]:
        await update.message.reply_text("No tienes solicitudes pendientes.")
        return

    messages = ["📋 Solicitudes pendientes:"]
    for idx, req in enumerate(prefs[chat_id], start=1):
        messages.append(f"{idx}. Origen: {req['origen']} Destino: {req['destino']} Fecha: {req['fecha']}")

    await update.message.reply_text("\n".join(messages))

async def delete_request(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    prefs = load_preferences()

    if chat_id not in prefs or not prefs[chat_id]:
        await update.message.reply_text("No tienes solicitudes para eliminar.")
        return ConversationHandler.END

    messages = ["🗑 Selecciona el número de la solicitud que deseas eliminar:"]
    for idx, req in enumerate(prefs[chat_id], start=1):
        messages.append(f"{idx}. Origen: {req['origen']} Destino: {req['destino']} Fecha: {req['fecha']}")

    await update.message.reply_text("\n".join(messages))
    return DELETE_REQUEST

async def delete_request_confirm(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    prefs = load_preferences()

    try:
        index = int(update.message.text) - 1
        if 0 <= index < len(prefs[chat_id]):
            del prefs[chat_id][index]
            if not prefs[chat_id]:
                del prefs[chat_id]

            save_preferences(prefs)
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

def main():
    try:
        # Build application with your token
        application = Application.builder().token(BOT_TOKEN).build()

        # Add handlers
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

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("view", view_requests))
        application.add_handler(conv_handler)
        application.add_handler(delete_handler)

        # Initialize bot before polling
        print("🤖 Bot en ejecución...")
        # Removed initialize() call since run_polling handles it
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
            drop_pending_updates=True
        )
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    main()
