from time import sleep

import vk_api.exceptions
from requests.exceptions import ReadTimeout, ConnectionError
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType, VkBotEvent
from vk_api.utils import get_random_id
from event import Event

import logger as log
import message_templates

logger = log.get_logger(__name__)


def _check_member_added(event: VkBotEvent, member_id: int) -> bool:
    """Проверить является ли событие event добавлением пользователя member_id"""
    return ("action" in event.obj["message"]) and \
           ("type" in event.obj["message"]["action"]) and \
           event.obj["message"]["action"]["type"] == "chat_invite_user" and \
           event.obj["message"]["action"]["member_id"] == member_id


class VKBot:
    def __init__(self, service_name, token, events):
        self.service_name = service_name
        self.events = events
        self.token = token
        try:
            self.vk_session = VkApi(token=token)
            self.group_id = self.get_group_id()
            self.longpoll = VkBotLongPoll(self.vk_session, self.group_id)
            self.vk = self.vk_session.get_api()
        except (ReadTimeout, ConnectionError):
            self.reconnect()

    def get_group_id(self) -> int:
        group_info = self.vk_session.method("groups.getById")[0]
        group_id = group_info["id"]
        return group_id

    def send(self, user_id: int, message: str, **kwargs):
        try:
            random_id = get_random_id()
            self.vk.messages.send(peer_id=user_id, message=message, random_id=random_id, **kwargs)
            logger.debug(f"Для {user_id} {self.service_name} отправлено сообщение")

        except (ReadTimeout, ConnectionError, vk_api.exceptions.ApiHttpError) as exc:
            if isinstance(exc, vk_api.exceptions.ApiHttpError):
                logger.warning(f"При отправке {user_id} {self.service_name} произошла ошибка:\n{exc}")
            self.reconnect()
            self.send(user_id, message, **kwargs)

        except vk_api.exceptions.ApiError as exc:
            if exc.code in (7, 901):
                # код 7 - бот удален из беседы
                # код 901 - пользователь ограничил число лиц которые могут ему писать
                self.events.append(Event.DELETE_GROUP(
                    service_name=self.service_name,
                    user_id=user_id))
            else:
                logger.warning(f"При отправке {user_id} {self.service_name} произошла ошибка:\n{exc}")

    def reconnect(self, recon_max: int = 5, recon_time: int = 60, count: int = 1):
        if count == 1:
            logger.info(f"Соединение разорвано")
        try:
            self.vk_session = VkApi(token=self.token)
            self.group_id = self.get_group_id()
            self.longpoll = VkBotLongPoll(self.vk_session, self.group_id)
            self.vk = self.vk_session.get_api()

        except (ReadTimeout, ConnectionError, vk_api.exceptions.ApiHttpError) as exc:
            if isinstance(exc, vk_api.exceptions.ApiHttpError):
                logger.warning(f"При переподключении {self.service_name} произошла ошибка:\n{exc}")

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

    def handle_massage(self, msg, user_id):
        msg = msg.lower().strip()
        if "  " in msg:
            msg = " ".join(msg.split())

        # Ответ на сообщения
        if msg.startswith("/sl "):

            logger.debug(f"От {user_id} {self.service_name} получена команда: {msg}")

            msg = msg.replace("/sl ", "")

            if msg.startswith("help"):
                self.send(user_id, message_templates.HELP_COMMAND)

            elif msg.startswith("info"):
                self.send(user_id, message_templates.INFO_COMMAND)

            elif msg.startswith("group "):
                group_name = msg.replace("group ", "").upper().replace(" ", "")
                self.events.append(Event.SET_GROUP(
                    service_name=self.service_name,
                    user_id=user_id,
                    group_name=group_name))

            elif msg.startswith("style "):
                style_id = msg.replace("style ", "")
                self.events.append(Event.SET_STYLE(
                    service_name=self.service_name,
                    user_id=user_id,
                    style_id=style_id))

            elif msg.startswith("adv"):
                self.events.append(Event.SET_ADV(
                    service_name=self.service_name,
                    user_id=user_id))

            elif msg.startswith("table"):
                group_name = msg.replace("table", "").upper().replace(" ", "")
                group_name = group_name if group_name else None
                self.events.append(Event.SEND_TABLE(
                    service_name=self.service_name,
                    user_id=user_id,
                    group_name=group_name))

            else:
                self.send(user_id, message_templates.UNKNOWN_COMMAND)

    def pooling(self):
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.obj["message"]["text"]
                user_id = event.obj["message"]["peer_id"]

                if msg:
                    self.handle_massage(msg, user_id)

                if _check_member_added(event=event, member_id=-self.group_id):
                    logger.debug(f"Бот добавлен в {user_id} {self.service_name}")

                    self.send(user_id, message_templates.BOT_ADD_EVENT)

    def main_loop(self):
        logger.info(f"Сервис {self.service_name} запущен")
        while True:
            try:
                self.pooling()

            except (ReadTimeout, ConnectionError, vk_api.exceptions.ApiHttpError):
                self.reconnect()

            except:
                logger.exception('')


if __name__ == "__main__":
    from config import VK_TOKEN

    logger = log.setup_applevel_logger()
    bot = VKBot(token=VK_TOKEN, events=[], service_name="vk")
    bot.main_loop()
