from time import sleep

import vk_api.exceptions
from requests.exceptions import ReadTimeout, ConnectionError
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

import logger as log
from config import BOT_ADD_TEXT, HELP_TEXT, INFO_TEXT, UNKNOWN_TEXT

logger = log.get_logger(__name__)


class VKBot:
    def __init__(self, token, group_id, events):
        self.events = events
        self.token = token
        self.group_id = group_id
        self.vk_session = VkApi(token=token)
        self.longpoll = VkBotLongPoll(self.vk_session, group_id)
        self.vk = self.vk_session.get_api()

    def send(self, peer_id, text):
        try:
            random_id = get_random_id()
            self.vk.messages.send(peer_id=peer_id, message=text, random_id=random_id)
            logger.debug(f"Для {peer_id} отправлено сообщение")
        except (ReadTimeout, ConnectionError):
            self.reconnect()
            self.send(peer_id, text)
        except vk_api.exceptions.ApiError as exc:
            if exc.code == 7:
                # код 7 - бот удален из беседы
                self.events.delete_group.append(peer_id)

    def reconnect(self, recon_max=5, recon_time=60, count=1):
        if count == 1:
            logger.info(f"Соединение разорвано")
        try:
            self.vk_session = VkApi(token=self.token)
            self.longpoll = VkBotLongPoll(self.vk_session, self.group_id)
            self.vk = self.vk_session.get_api()

        except (ReadTimeout, ConnectionError):
            count += 1

            if count % (recon_max*2) == 0:
                sleep(recon_time*120)
            elif count % recon_max == 0:
                sleep(recon_time)

            sleep(recon_time // 10)
            self.reconnect(count=count)

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

                        msg = msg.lower()
                        # Ответ на сообщения
                        if msg.startswith("/sl "):

                            logger.debug(f"От {peer_id} получена команда: {msg}")

                            msg = msg.replace("/sl ", "")

                            if msg.startswith("help"):
                                self.send(peer_id, HELP_TEXT)

                            elif msg.startswith("info"):
                                self.send(peer_id, INFO_TEXT)

                            elif msg.startswith("group "):
                                group_name = msg.replace("group ", "").upper()
                                self.events.set_group.append([peer_id, group_name])

                            elif msg.startswith("style "):
                                style_id = msg.replace("style ", "")
                                self.events.set_style.append([peer_id, style_id])

                            elif msg.startswith("adv"):
                                self.events.set_adv.append(peer_id)

                            elif msg.startswith("table"):
                                self.events.send_table.append(peer_id)

                            else:
                                self.send(peer_id, UNKNOWN_TEXT)

                        if ("action" in event.obj["message"]) and ("type" in event.obj["message"]["action"]):
                            # Действие при добавлении бота в беседу
                            if event.obj["message"]["action"]["type"] == "chat_invite_user" and \
                                    event.obj["message"]["action"]["member_id"] == -209119751:
                                logger.debug(f"Бот добавлен в {peer_id}")

                                self.send(peer_id, BOT_ADD_TEXT)
                                continue

            except (ReadTimeout, ConnectionError):
                self.reconnect()
            except KeyboardInterrupt:
                break
            except:
                logger.exception('')


if __name__ == "__main__":
    from config import TOKEN, GROUP_ID

    logger = log.setup_applevel_logger()
    bot = VKBot(token=TOKEN, group_id=GROUP_ID, events=[])
    bot.main_loop()
