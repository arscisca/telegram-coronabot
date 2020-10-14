import sys
import logging
from telegram.ext import Updater

import coronabot.handlers as handlers


def main(token):
    """Main function"""
    # Setup logging
    logging.basicConfig(filename='../logs/backend.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
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
    token = ''
    try:
        token = sys.argv[1]
    except IndexError:
        print("Please pass Telegram API token as a program argument.")
        exit(-1)
    main(token)
