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

    def send(self, peer_id: int, message: str, **kwargs):
        try:
            random_id = get_random_id()
            self.vk.messages.send(peer_id=peer_id, message=message, random_id=random_id, **kwargs)
            logger.debug(f"Для {peer_id} отправлено сообщение")
        except (ReadTimeout, ConnectionError):
            self.reconnect()
            self.send(peer_id, message, **kwargs)
        except vk_api.exceptions.ApiError as exc:
            if exc.code == 7:
                # код 7 - бот удален из беседы
                self.events.delete_group.append(peer_id)
            elif exc.code == 901:
                # код 901 - пользователь ограничил число лиц которые могут ему писать
                self.events.delete_group.append(peer_id)
            else:
                logger.warning(f"При отправке {peer_id} произошла ошибка:\n{exc}")

    def reconnect(self, recon_max: int = 5, recon_time: int = 60, count: int = 1):
        if count == 1:
            logger.info(f"Соединение разорвано")
        try:
            self.vk_session = VkApi(token=self.token)
            self.group_id = self.get_group_id()
            self.longpoll = VkBotLongPoll(self.vk_session, self.group_id)
            self.vk = self.vk_session.get_api()

        except (ReadTimeout, ConnectionError):
            count += 1

            if count % (recon_max * 4) == 0:
                sleep(recon_time * 120)
            elif count % (recon_max * 2) == 0:
                sleep(recon_time * 10)
            elif count % recon_max == 0:
                sleep(recon_time)

            sleep(recon_time // 10)
            self.reconnect(recon_max=recon_max, recon_time=recon_time, count=count)

        else:
            logger.info(f"Соединение восстановлено спустя {count} попыт(ку/ки/ок)")

    def main_loop(self):
        logger.info("bot_loop запущен")
        while True:
            try:
                for event in self.longpoll.listen():
                    if event.type == VkBotEventType.MESSAGE_NEW:
                        msg = event.obj["message"]["text"]
                        peer_id = event.obj["message"]["peer_id"]

                        msg = msg.lower().strip()
                        if "  " in msg:
                            msg = " ".join(msg.split())

                        # Ответ на сообщения
                        if msg.startswith("/sl "):

                            logger.debug(f"От {peer_id} получена команда: {msg}")

                            msg = msg.replace("/sl ", "")

                            if msg.startswith("help"):
                                self.send(peer_id, message_templates.HELP_COMMAND)

                            elif msg.startswith("info"):
                                self.send(peer_id, message_templates.INFO_COMMAND)

                            elif msg.startswith("group "):
                                group_name = msg.replace("group ", "").upper().replace(" ", "")
                                self.events.append(Event.SET_GROUP(
                                    service=self.service_name,
                                    user_id=peer_id,
                                    group_name=group_name))

                            elif msg.startswith("style "):
                                style_id = msg.replace("style ", "")
                                self.events.append(Event.SET_STYLE(
                                    service=self.service_name,
                                    user_id=peer_id,
                                    style_id=style_id))

                            elif msg.startswith("adv"):
                                self.events.append(Event.SET_ADV(
                                    service=self.service_name,
                                    user_id=peer_id))

                            elif msg.startswith("table"):
                                self.events.append(Event.SEND_TABLE(
                                    service=self.service_name,
                                    user_id=peer_id))

                            else:
                                self.send(peer_id, message_templates.UNKNOWN_COMMAND)

                        if _check_member_added(event=event, member_id=-self.group_id):
                            logger.debug(f"Бот добавлен в {peer_id}")

                            self.send(peer_id, message_templates.BOT_ADD_EVENT)
                            continue

            except (ReadTimeout, ConnectionError):
                self.reconnect()

            except:
                logger.exception('')


if __name__ == "__main__":
    from config import VK_TOKEN

    logger = log.setup_applevel_logger()
    bot = VKBot(token=VK_TOKEN, events=[], service_name="vk")
    bot.main_loop()
