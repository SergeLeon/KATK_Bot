from time import sleep

from telebot import TeleBot
from telebot.apihelper import ApiTelegramException
from requests.exceptions import ReadTimeout, ConnectionError

from event import Event
import logger as log
import message_templates
from table_formatter import prepare_group_name

logger = log.get_logger(__name__)


class TelegramBot:
    def __init__(self, service_name, token, events):
        self.service_name = service_name
        self.events = events
        self.token = token
        self.bot = TeleBot(self.token)
        try:
            self.connect()

        except (ReadTimeout, ConnectionError):
            self.reconnect()

    def send(self, user_id: int, message: str, **kwargs):
        try:
            self.bot.send_message(chat_id=user_id, text=message)
            logger.debug(f"Для {user_id} {self.service_name} отправлено сообщение")

        except (ReadTimeout, ConnectionError):
            self.reconnect()
            self.send(user_id, message, **kwargs)

        except ApiTelegramException as exc:
            error_code = exc.error_code
            if error_code == 403:
                # код 403 - бот заблокирован пользователем или удален из беседы
                self.events.append(
                    Event.DELETE_USER(
                        service_name=self.service_name,
                        user_id=user_id
                    )
                )

            elif error_code == 400 and "supergroup" in exc.description:
                # код 400 описание "Bad Request: group chat was upgraded to a supergroup chat"
                new_user_id = exc.result_json["parameters"]["migrate_to_chat_id"]
                self.events.append(
                    Event.CHANGE_ID(
                        service_name=self.service_name,
                        user_id=user_id,
                        new_user_id=new_user_id
                    )
                )
                self.send(new_user_id, message, **kwargs)

            else:
                logger.warning(f"При отправке {user_id} {self.service_name} произошла ошибка:\n{exc.result_json}")

    def connect(self):
        self.bot = TeleBot(self.token)
        self.bot.get_me()  # Делает запрос для проверки соединения
        self.register_handlers()

    def reconnect(self, recon_max: int = 5, recon_time: int = 60, count: int = 1):
        if count == 1:
            logger.info("Соединение разорвано")
        try:
            self.bot.stop_bot()
            self.connect()

        except (ReadTimeout, ConnectionError):
            count += 1

            if count % (recon_max * 4) == 0:
                sleep(recon_time * 15)
            elif count % (recon_max * 2) == 0:
                sleep(recon_time * 10)
            elif count % recon_max == 0:
                sleep(recon_time)

            sleep(recon_time // 10)
            self.reconnect(recon_max=recon_max, recon_time=recon_time, count=count)

        else:
            logger.info(f"Соединение восстановлено спустя {count} попыт(ку/ки/ок)")

    def register_handlers(self):
        self.bot.register_message_handler(self.handle_message, content_types=["text"])
        self.bot.register_chat_join_request_handler(self.handle_chat_join)

    def handle_chat_join(self, message):
        user_id = message.chat.id

        logger.debug(f"Бот добавлен в {user_id} {self.service_name}")

        self.send(user_id, f"{message_templates.INFO_COMMAND}\n"
                           f"{message_templates.HELP_COMMAND}")

    def handle_message(self, message):
        msg = message.text
        user_id = message.chat.id

        msg = msg.lower().strip()
        if "  " in msg:
            msg = " ".join(msg.split())

        logger.debug(f"От {user_id} {self.service_name} получена команда: {msg}")

        # Ответ на сообщения
        if msg == "/start":
            self.send(user_id, (f"{message_templates.INFO_COMMAND}\n"
                                f"{message_templates.HELP_COMMAND}"))
        elif msg.startswith("/sl "):

            msg = msg.replace("/sl ", "")

            if msg.startswith("help"):
                self.send(user_id, message_templates.HELP_COMMAND)

            elif msg.startswith("info"):
                self.send(user_id, message_templates.INFO_COMMAND)

            elif msg.startswith("group add "):
                group_name = msg.replace("group add ", "").upper().replace(" ", "")
                group_name = prepare_group_name(group_name)
                self.events.append(
                    Event.ADD_GROUP(
                        service_name=self.service_name,
                        user_id=user_id,
                        group_name=group_name
                    )
                )

            elif msg.startswith("group del "):
                group_name = msg.replace("group del ", "").upper().replace(" ", "")
                group_name = prepare_group_name(group_name)
                self.events.append(
                    Event.DEL_GROUP(
                        service_name=self.service_name,
                        user_id=user_id,
                        group_name=group_name
                    )
                )

            elif msg.startswith("group "):
                group_name = msg.replace("group ", "").upper().replace(" ", "")
                group_name = prepare_group_name(group_name)
                self.events.append(
                    Event.SET_GROUP(
                        service_name=self.service_name,
                        user_id=user_id,
                        group_name=group_name
                    )
                )

            elif msg.startswith("style "):
                style_id = msg.replace("style ", "")
                self.events.append(
                    Event.SET_STYLE(
                        service_name=self.service_name,
                        user_id=user_id,
                        style_id=style_id
                    )
                )

            elif msg.startswith("adv"):
                self.events.append(
                    Event.SET_ADV(
                        service_name=self.service_name,
                        user_id=user_id
                    )
                )

            elif msg.startswith("table"):
                group_name = msg.replace("table", "").upper().replace(" ", "")
                groups = (prepare_group_name(group_name),) if group_name else None
                self.events.append(
                    Event.SEND_TABLE(
                        service_name=self.service_name,
                        user_id=user_id,
                        groups=groups
                    )
                )

            else:
                self.send(user_id, message_templates.UNKNOWN_COMMAND)

    def main_loop(self):
        logger.info(f"Сервис {self.service_name} запущен")
        while True:
            try:
                self.bot.polling()

            except (ReadTimeout, ConnectionError):
                self.reconnect()

            except:
                logger.exception('')
                self.reconnect()


if __name__ == "__main__":
    from config import TELEGRAM_TOKEN

    logger = log.setup_applevel_logger()
    tgbot = TelegramBot(token=TELEGRAM_TOKEN, events=[], service_name="telegram")
    tgbot.main_loop()
