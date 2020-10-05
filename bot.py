import logging
from telegram.ext import Updater

import handlers


def read_token(file):
    """Read Telegram API token from specified file
    Args:
        file (file)
    Return:
        str: API token
    """
    return file.readline().strip()


def main():
    """Main function"""
    # Setup logging
    logging.basicConfig(filename='logs/backend.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    # API token
    with open('.token', 'r') as f:
        token = read_token(f)
    # Initialize bot
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(handlers.conversation)
    # Start bot
    print("Starting bot...")
    updater.start_polling()
    print("Started bot!")
    updater.idle()
    print("Stopped bot")


if __name__ == '__main__':
    main()