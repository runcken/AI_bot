from environs import Env
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


def start(update, context):
    user = update.message.from_user
    update.message.reply_text(f'Здравствуйте, {user.first_name}!')


def echo(update, context):
    update.message.reply_text(update.message.text)


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    env = Env()
    env.read_env()
    TOKEN = env.str('TG_TOKEN')

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dp.add_error_handler(error)

    print('Бот @{bot_info.username} запущен...')
    updater.start_polling()
    updater.idle()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger()


if __name__ == '__main__':
    main()