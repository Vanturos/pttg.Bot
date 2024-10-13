# Импортируем необходимые библиотечки - а из telegram.ext - конкретные модули библиотеки
import logging
import os
import subprocess
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)
import paramiko
import psycopg2
from psycopg2 import Error

# Задаем конфигурацию логам
logging.basicConfig(
    filename='bot.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Подгружаем локальные переменные
load_dotenv()

MESS_MAX_LENGTH = 4096
TELEGRAM_TOKEN = os.getenv('TOKEN')
SSH_HOST = os.getenv('RM_HOST')
SSH_PORT = int(os.getenv('RM_PORT'))
SSH_USER = os.getenv('RM_USER')
SSH_PASSWORD = os.getenv('RM_PASSWORD')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_DATABASE = os.getenv('DB_DATABASE')
DB_REPL_USER = os.getenv('DB_REPL_USER')
DB_REPL_PASSWORD = os.getenv('DB_REPL_PASSWORD')
DB_REPL_HOST = os.getenv('DB_REPL_HOST')
DB_REPL_PORT = os.getenv('DB_REPL_PORT')

# Состояния хэндлеров 
VERIFY_PASSWORD, FIND_EMAIL, FIND_PHONE, CONFIRM_SAVE = range(4)
APT_LIST = 0

def create_ssh_client():
    # Создаем клиент ssh для общения с remote host при помощи paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=SSH_HOST,
        port=SSH_PORT,
        username=SSH_USER,
        password=SSH_PASSWORD,
    )
    return ssh

def is_strong_password(password):
    # Проверяем подходит ли пароль парольной политике
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*()]', password):
        return False
    return True

def verify_password_start(update: Update, context: CallbackContext):
    # Просим пользователя ввести пароль
    update.message.reply_text('Пожалуйста, введите пароль:')
    return VERIFY_PASSWORD

def verify_password_check(update: Update, context: CallbackContext):
    # Проверяем пароль
    password = update.message.text
    if is_strong_password(password):
        update.message.reply_text('Пароль сложный.')
    else:
        update.message.reply_text('Пароль простой.')
    return ConversationHandler.END

def find_email_start(update: Update, context: CallbackContext):
    # просим пользователя ввести адреса
    update.message.reply_text('Пожалуйста, введите текст для поиска email-адресов:')
    return FIND_EMAIL

def find_email_execute(update: Update, context: CallbackContext):
    # Ищем email адреса по regexp
    text = update.message.text
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    emails = re.findall(email_pattern, text)
    if emails:
        unique_emails = list(set(emails))
        context.user_data['found_emails'] = unique_emails  # Сохраняем найденные email в контексте
        update.message.reply_text('Найдены следующие email-адреса:\n' + '\n'.join(unique_emails) + '\nХотите сохранить их в базу данных? (да/нет)')
        return CONFIRM_SAVE
    else:
        update.message.reply_text('Email-адреса не найдены. Операция завершена.')
        return ConversationHandler.END

def find_phone_number_start(update: Update, context: CallbackContext):
    # Просим пользователя прислать нам телефоны
    update.message.reply_text('Пожалуйста, введите текст для поиска номеров телефонов:')
    return FIND_PHONE

def find_phone_number_execute(update: Update, context: CallbackContext):
    # Ищем телефоны по regexp и отправляем уникальные
    text = update.message.text
    phone_pattern = r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
    phones = re.findall(phone_pattern, text)
    logger.error(phones)
    if phones:
        unique_phones = list(set(phones))
        context.user_data['found_phones'] = unique_phones  # Сохраняем найденные телефоны в контексте
        update.message.reply_text('Найдены следующие номера телефонов:\n' + '\n'.join(unique_phones) + '\nХотите сохранить их в базу данных? (да/нет)')
        return CONFIRM_SAVE
    else:
        update.message.reply_text('Номера телефонов не найдены. Операция завершена.')
        return ConversationHandler.END

def confirm_save(update: Update, context: CallbackContext):
    # Обработка подтверждения сохранения
    user_response = update.message.text.lower()
    
    if user_response == 'да':
        found_emails = context.user_data.get('found_emails')
        found_phones = context.user_data.get('found_phones')
        try:
            connection = psycopg2.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_DATABASE
            )
            cursor = connection.cursor()
            if found_emails:
                for email in found_emails:
                    cursor.execute("INSERT INTO emails (email) VALUES (%s)", (email,))
            if found_phones:
                for phone in found_phones:
                    cursor.execute("INSERT INTO phones (phone) VALUES (%s)", (phone,))
            connection.commit()
            cursor.close()
            connection.close()
            update.message.reply_text('Данные успешно сохранены в базу данных.')
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Ошибка при сохранении в базу данных: {e}")
            update.message.reply_text('Ошибка при сохранении данных в базу данных.')
            return ConversationHandler.END
    elif user_response == 'нет':
        update.message.reply_text('Сохранение отменено. Операция завершена.')
        return ConversationHandler.END
    else:
        update.message.reply_text('Пожалуйста, ответьте "да" или "нет".')
        return CONFIRM_SAVE

def get_release(update: Update, context: CallbackContext):
    # Отсылаем информацию о системе: о дистрибутиве
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('lsb_release -a')
        output = stdout.read().decode()
        update.message.reply_text(f'Информация о релизе:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_release: {e}')
        update.message.reply_text('Произошла ошибка при получении информации о релизе.')

def get_uname(update: Update, context: CallbackContext):
    # Отсылаем информацию о удаленной системе: о ядре
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('uname -a')
        output = stdout.read().decode()
        update.message.reply_text(f'Информация о системе:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_uname: {e}')
        update.message.reply_text('Произошла ошибка при получении информации о системе.')

def get_uptime(update: Update, context: CallbackContext):
    # Отсылаем время работы удаленной системы
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('uptime -p')
        output = stdout.read().decode()
        update.message.reply_text(f'Время работы системы:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_uptime: {e}')
        update.message.reply_text('Произошла ошибка при получении времени работы системы.')


def get_df(update: Update, context: CallbackContext):
    # Отсылаем информацию о файловой системе на удаленном хосте
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('df -h')
        output = stdout.read().decode()
        update.message.reply_text(f'Состояние файловой системы:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_df: {e}')
        update.message.reply_text('Произошла ошибка при получении информации о файловой системе.')

def get_free(update: Update, context: CallbackContext):
    # Отсылаем информацию о оперативной памяти на удаленной системе
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('free -h')
        output = stdout.read().decode()
        update.message.reply_text(f'Состояние оперативной памяти:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_free: {e}')
        update.message.reply_text('Произошла ошибка при получении информации о памяти.')

def get_mpstat(update: Update, context: CallbackContext):
    # отсылаем информацию о производительности удаленой системы
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('mpstat')
        output = stdout.read().decode()
        update.message.reply_text(f'Производительность системы:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_mpstat: {e}')
        update.message.reply_text('Произошла ошибка при получении информации о производительности.')

def get_w(update: Update, context: CallbackContext):
    # Отсылаем информацию о текущих пользователях удаленной системы
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('w')
        output = stdout.read().decode()
        update.message.reply_text(f'Пользователи в системе:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_w: {e}')
        update.message.reply_text('Произошла ошибка при получении информации о пользователях.')

def get_auths(update: Update, context: CallbackContext):
    # Отсылаем информацию о последних 10 входах в удаленную систему
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('last -n 10')
        output = stdout.read().decode()
        update.message.reply_text(f'Последние 10 входов в систему:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_auths: {e}')
        update.message.reply_text('Произошла ошибка при получении логов входа.')

def get_critical(update: Update, context: CallbackContext):
    # Отсылаем информацию о последних пяти критических событих
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('journalctl -p crit -n 5')
        output = stdout.read().decode()
        update.message.reply_text(f'Последние 5 критических событий:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_critical: {e}')
        update.message.reply_text('Произошла ошибка при получении критических событий.')

def get_ps(update: Update, context: CallbackContext):
    # Отсылаем информацию о запущенных процессах
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('ps aux')
        output = stdout.read().decode()
        update.message.reply_text(f'Запущенные процессы:')
        for x in range(0, len(output), MESS_MAX_LENGTH):
                mess = output[x: x + MESS_MAX_LENGTH]
                update.message.reply_text(mess)
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_ps: {e}')
        update.message.reply_text('Произошла ошибка при получении информации о процессах.')

def get_ss(update: Update, context: CallbackContext):
    # Отсылаем информацию о портах на машине
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('ss -tuln')
        output = stdout.read().decode()
        update.message.reply_text(f'Используемые порты:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_ss: {e}')
        update.message.reply_text('Произошла ошибка при получении информации о портах.')


def get_services(update: Update, context: CallbackContext):
    # Отсылаем информацию о сервисах, запущенных на удаленной машине
    try:
        ssh = create_ssh_client()
        stdin, stdout, stderr = ssh.exec_command('systemctl list-units --type=service --state=running')
        output = stdout.read().decode()
        update.message.reply_text(f'Запущенные сервисы:\n{output}')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_services: {e}')
        update.message.reply_text('Произошла ошибка при получении информации о сервисах.')

def get_apt_list_start(update: Update, context: CallbackContext):
    # Узнаем у пользователя, какую опцию он хочет использовать
    update.message.reply_text('Введите название пакета или отправьте "все" для вывода всех пакетов:')
    return APT_LIST

def get_apt_list_execute(update: Update, context: CallbackContext):
    # Смотрим пакеты по ssh и отправляем их пользователю
    package_name = update.message.text.strip()
    try:
        ssh = create_ssh_client()
        if package_name.lower() == 'все':
            stdin, stdout, stderr = ssh.exec_command('apt list --installed')
            output = stdout.read().decode()
            update.message.reply_text(f'Установленные пакеты:')
            for x in range(0, len(output), MESS_MAX_LENGTH):
                mess = output[x: x + MESS_MAX_LENGTH]
                update.message.reply_text(mess)
        else:
            stdin, stdout, stderr = ssh.exec_command(f'apt list --installed | grep {package_name}')
            output = stdout.read().decode()
            if output:
                update.message.reply_text(f'Информация о пакете "{package_name}":\n{output}')
            else:
                update.message.reply_text(f'Пакет "{package_name}" не найден.')
        ssh.close()
    except Exception as e:
        logger.error(f'Error in get_apt_list: {e}')
        update.message.reply_text('Произошла ошибка при получении информации о пакетах.')
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text('Операция отменена.')
    return ConversationHandler.END

def get_emails(update: Update, context: CallbackContext):
    try:
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_DATABASE
        )
        cursor = connection.cursor()
        cursor.execute("SELECT email FROM emails;")
        emails = cursor.fetchall()
        if emails:
            email_list = "\n".join(email[0] for email in emails)
            update.message.reply_text(f"Найденные email-адреса:\n{email_list}")
        else:
            update.message.reply_text("Email-адреса не найдены.")
    except (Exception, psycopg2.Error) as error:
        logger.error(f"Ошибка при получении email: {error}")
        update.message.reply_text("Произошла ошибка при получении email-адресов.")
    finally:
        if connection:
            cursor.close()
            connection.close()

def get_phone_numbers(update: Update, context: CallbackContext):
    try:
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_DATABASE
        )
        cursor = connection.cursor()
        cursor.execute("SELECT phone FROM phones;")
        phones = cursor.fetchall()
        if phones:
            phone_list = "\n".join(phone[0] for phone in phones)
            update.message.reply_text(f"Найденные номера телефонов:\n{phone_list}")
        else:
            update.message.reply_text("Номера телефонов не найдены.")
    except (Exception, psycopg2.Error) as error:
        logger.error(f"Ошибка при получении номеров телефонов: {error}")
        update.message.reply_text("Произошла ошибка при получении номеров телефонов.")
    finally:
        if connection:
            cursor.close()
            connection.close()

def get_repl_logs(update: Update, context: CallbackContext):
    try:
        command = "grep repl /var/log/postgresql/postgresql-15-main.log | tail -n 30"
        logs = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if logs.returncode == 0:
            logs_output = logs.stdout
            if logs_output:
                update.message.reply_text("Логи репликации:\n")
                messages = [logs_output[i:i + MESS_MAX_LENGTH] for i in range(0, len(logs_output), MESS_MAX_LENGTH)]
                for mess in messages:
                    update.message.reply_text(mess)
            else:
                update.message.reply_text("Логи репликации отсутствуют.")
        else:
            update.message.reply_text("Ошибка при получении логов.")
            logger.error(logs.stderr)
    except subprocess.CalledProcessError as e:
        update.message.reply_text(f"Ошибка при получении логов: {str(e)}")


def main():
    updater = Updater(TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher

    # Хэндлер для того, чтобы получить пароль от пользователя
    conv_handler_password = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_password_start)],
        states={
            VERIFY_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, verify_password_check)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Хэндлер для того, чтобы выбрать опцию показать ли все пакеты, или же выборочно.
    conv_handler_apt_list = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', get_apt_list_start)],
        states={
            APT_LIST: [MessageHandler(Filters.text & ~Filters.command, get_apt_list_execute)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    # Хэндлер для того, чтобы корректно обрабатывать получение списка эмеил адресов и не только
    conv_handler_find_email = ConversationHandler(
        entry_points=[CommandHandler('find_email', find_email_start)],
        states={
            FIND_EMAIL: [MessageHandler(Filters.text & ~Filters.command, find_email_execute)],
            CONFIRM_SAVE: [MessageHandler(Filters.text & ~Filters.command, confirm_save)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    # Хэндлер для того, чтобы корректно обрабатывать получение списка телефонных номеров и не только
    conv_handler_find_phone = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', find_phone_number_start)],
        states={
            FIND_PHONE: [MessageHandler(Filters.text & ~Filters.command, find_phone_number_execute)],
            CONFIRM_SAVE: [MessageHandler(Filters.text & ~Filters.command, confirm_save)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Создаем хэндлеры команд
    dispatcher.add_handler(conv_handler_password)
    dispatcher.add_handler(conv_handler_apt_list)
    dispatcher.add_handler(conv_handler_find_email)
    dispatcher.add_handler(conv_handler_find_phone)
    dispatcher.add_handler(CommandHandler('get_release', get_release))
    dispatcher.add_handler(CommandHandler('get_uname', get_uname))
    dispatcher.add_handler(CommandHandler('get_uptime', get_uptime))
    dispatcher.add_handler(CommandHandler('get_df', get_df))
    dispatcher.add_handler(CommandHandler('get_free', get_free))
    dispatcher.add_handler(CommandHandler('get_mpstat', get_mpstat))
    dispatcher.add_handler(CommandHandler('get_w', get_w))
    dispatcher.add_handler(CommandHandler('get_auths', get_auths))
    dispatcher.add_handler(CommandHandler('get_critical', get_critical))
    dispatcher.add_handler(CommandHandler('get_ps', get_ps))
    dispatcher.add_handler(CommandHandler('get_ss', get_ss))
    dispatcher.add_handler(CommandHandler('get_services', get_services))
    dispatcher.add_handler(CommandHandler('cancel', cancel))
    dispatcher.add_handler(CommandHandler('get_emails', get_emails))
    dispatcher.add_handler(CommandHandler('get_phone_numbers', get_phone_numbers))
    dispatcher.add_handler(CommandHandler('get_repl_logs', get_repl_logs))


    # Бот начинает слушать
    updater.start_polling()
    logger.info('Bot started.')
    updater.idle()

if __name__ == '__main__':
    main()
