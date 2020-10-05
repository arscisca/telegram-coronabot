import logging

from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters

# Conversation states
HOME, TRENDS, REPORTS, ERROR = range(4)


# Helper functions
def send_message(update: Update, context: CallbackContext, message, **kwargs):
    """Send a message in the chat that generated the update
    Args:
        update (Update)
        context (CallbackContext)
        message (str): textual message to be sent
        **kwargs: arbitrary keyword arguments
    """
    context.bot.send_message(update.effective_chat.id, message, **kwargs)


def send_photo(update: Update, context: CallbackContext, photo, **kwargs):
    """Send a photo in the chat that generated the update
    Args:
        update (Update)
        context (CallbackContext)
        photo (file): textual message to be sent
        **kwargs: arbitrary keyword arguments
    """
    context.bot.send_photo(update.effective_chat.id, photo, **kwargs)


# Generic callbacks
def cb_error_handler(update: Update, context: CallbackContext):
    """Error handler"""
    try:
        raise context.error
    except NotImplementedError as e:
        logging.warning("Request for a not implemented function", e)
        send_message(update, context, "Questa funzione non è ancora disponibile")
    except Exception as e:
        logging.error("An exception could not be handled", e)
        send_message(update, context,
                     "Si è verificato un errore. Consulta le informazioni del comando /help oppure "
                     "riavvia la conversazione con /start.")


def cb_not_implemented(update: Update, context: CallbackContext):
    """Placeholder for not implemented functions
    Args:
        update (Update)
        context (CallbackContext)
    Raise:
        NotImplementedError
    """
    raise NotImplementedError("Handler not implemented")


def cb_prompt_start(update: Update, context: CallbackContext):
    """Prompt the start of the conversation when bot is inactive."""
    send_message(update, context, "La conversazione non è attiva. Digita /start per avviarla.")


def cb_start(update: Update, context: CallbackContext):
    """Start the conversation"""
    cb_not_implemented(update, context)
    return HOME


def cb_stop(update: Update, context: CallbackContext):
    """Stop bot"""
    cb_not_implemented(update, context)
    return ConversationHandler.END


# Home state
def cb_home_help(update: Update, context: CallbackContext):
    """Help for the HOME state"""
    cb_not_implemented(update, context)
    return HOME


def cb_info(update: Update, context: CallbackContext):
    """Send info about the bot"""
    cb_not_implemented(update, context)
    return HOME


# Reports state
def cb_reports_help(update: Update, context: CallbackContext):
    """Help for the REPORTS state"""
    cb_not_implemented(update, context)
    return REPORTS


# Trends state
def cb_trends_help(update: Update, context: CallbackContext):
    """Help for the TRENDS state"""
    cb_not_implemented(update, context)
    return TRENDS


conversation = ConversationHandler(
    entry_points=[
        CommandHandler('start', cb_start),
        MessageHandler(Filters.all, cb_prompt_start)
    ],
    states={
        HOME: [
            CommandHandler('help', cb_home_help),
            MessageHandler(Filters.text('Aiuto'), cb_home_help)
        ],
        REPORTS: [],
        TRENDS: []
    },
    fallbacks=[]
)
