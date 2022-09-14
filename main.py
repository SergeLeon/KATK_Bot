from threading import Thread
from time import sleep

from dataclasses import dataclass

import logger as log
import message_templates
from config import VK_TOKEN, URL, CHECK_TIME
from data_parser import Parser, table_type
from database import DataBase
from table_formatter import table_to_str, tables_to_group_names, STYLES
from vk_bot import VKBot


@dataclass
class Events:
    set_group = []
    set_adv = []
    set_style = []
    send_table = []
    delete_group = []


logger = log.setup_applevel_logger()


class Main:
    def __init__(self):
        self.events = Events()
        self.bot = VKBot(token=VK_TOKEN, events=self.events)
        self.pars = Parser(URL)
        # хранит расписание
        self.tables: list = []
        # хранит названия групп
        self.group_names: list = []
        # хранит дату
        self.tables_date: str = ""
        self.update()

        # check_same_thread отключен т.к. только event_loop пишет в базу.
        self.db = DataBase("database.db", check_same_thread=False)

        logger.info("Приложение инициализировано")

    def update(self):
        self.tables = self.pars.get_tables()
        self.group_names = tables_to_group_names(self.tables)
        self.tables_date = self.pars.get_date()

    def parsing_loop(self):
        self.update()

        logger.info("parsing_loop запущен")
        while True:
            try:
                self.pars.update()

                new_tables = self.pars.get_tables()
                # Проверка на существование информации
                if tables_to_group_names(new_tables):
                    old_tables = self.tables

                    new_tables.sort(key=lambda table: table[0][1])
                    old_tables.sort(key=lambda table: table[0][1])

                    if self.pars.get_date() != self.tables_date:
                        self.update()
                        logger.info("Все таблицы обновлены")
                        logger.debug(f"Дата: {self.tables_date}")
                        for group_info in self.db.get_adverted():
                            self.events.send_table.append(group_info["peer_id"])

                    elif new_tables != old_tables:

                        logger.info("Таблицы обновлены")

                        updated_groups = []
                        for new_table, old_table in zip(new_tables, old_tables):
                            if new_table != old_table:
                                updated_groups.append(new_table[0][1])

                        logger.debug(f"для {updated_groups}")

                        self.update()

                        for group_info in self.db.get_adverted():
                            if group_info["name"] in updated_groups:
                                self.events.send_table.append(group_info["peer_id"])

                else:
                    logger.warning("Парсер ничего не вернул")

            except:
                logger.exception('')

            sleep(CHECK_TIME)

    def _find_group_name(self, finding_group: str) -> str:
        for group in self.group_names:
            if finding_group in group:
                return group
        return ""

    def _find_group_table(self, group_name: str) -> table_type:
        for table in self.tables:
            if table[0][1] == group_name:
                return table

    def _bot_send_table(self, peer_id: int, group_name: str, style_id: int):
        self.bot.send(peer_id=peer_id,
                      message=table_to_str(
                          table=self._find_group_table(group_name),
                          style_id=style_id,
                          date=self.pars.get_date(),
                          consider_column_width=False))

    def __set_group(self, event):
        peer_id, group_name = event

        norm_group = self._find_group_name(group_name)
        if bool(norm_group):

            if self.db.get_by_peer_id(peer_id):
                self.db.set_by_peer_id(peer_id=peer_id, field="name", value=norm_group)
            else:
                self.db.add_group(peer_id=peer_id, group_name=norm_group)

            self.bot.send(peer_id=peer_id, message=message_templates.GROUP_CHANGED_TO.format(group=norm_group))

        else:
            self.bot.send(peer_id=peer_id, message=message_templates.GROUP_NOT_FOUND.format(group=group_name))

    def __set_style(self, event):
        peer_id, style_id = event
        if style_id.isnumeric() and (int(style_id) in STYLES):
            style_id = int(style_id)

            if self.db.get_by_peer_id(peer_id):
                self.db.set_by_peer_id(peer_id=peer_id, field="style_id", value=style_id)
                self.bot.send(peer_id=peer_id, message=message_templates.STYLE_CHANGED_TO.format(style=style_id))
            else:
                self.bot.send(peer_id=peer_id, message=message_templates.NEED_SELECT_GROUP)
        else:
            self.bot.send(peer_id=peer_id, message=message_templates.STYLE_NOT_FOUND.format(style=style_id))

    def __set_adv(self, peer_id: int):
        group_info = self.db.get_by_peer_id(peer_id)
        if group_info:
            group_adv = not group_info["adv"]
            self.db.set_by_peer_id(peer_id=peer_id, field="adv", value=group_adv)

            if group_adv:
                self.bot.send(peer_id=peer_id, message=message_templates.ADVERTS_ON)
            else:
                self.bot.send(peer_id=peer_id, message=message_templates.ADVERTS_OFF)
        else:
            self.bot.send(peer_id=peer_id, message=message_templates.NEED_SELECT_GROUP)

    def __send_table(self, peer_id: int):
        if self.tables and self.group_names:
            group_info = self.db.get_by_peer_id(peer_id)
            if group_info:
                if group_info["name"] in self.group_names:
                    self._bot_send_table(peer_id=group_info["peer_id"],
                                         group_name=group_info["name"],
                                         style_id=group_info["style_id"])
                else:
                    self.bot.send(peer_id=peer_id,
                                  message=f"{message_templates.GROUP_NOT_FOUND.format(group=group_info['name'])}\n"
                                          f"{message_templates.NEED_SELECT_GROUP}")
            else:
                self.bot.send(peer_id=peer_id, message=message_templates.NEED_SELECT_GROUP)
        else:
            self.bot.send(peer_id=peer_id, message=message_templates.NO_INFORMATION)

    def __delete_group(self, peer_id: int):
        self.db.delete_by_peer_id(peer_id=peer_id)

    def event_loop(self):
        logger.info("event_loop запущен")
        while True:
            try:
                # Отлов ивентов на установку группы
                for event in self.events.set_group:
                    self.__set_group(event)
                    self.events.set_group.remove(event)

                # Отлов ивентов на установку темы
                for event in self.events.set_style:
                    self.__set_style(event)
                    self.events.set_style.remove(event)

                # Отлов ивентов на изменение режима оповещений
                for peer_id in self.events.set_adv:
                    self.__set_adv(peer_id)
                    self.events.set_adv.remove(peer_id)

                # Отлов ивентов на отправку таблицы
                for peer_id in self.events.send_table:
                    self.__send_table(peer_id)
                    self.events.send_table.remove(peer_id)

                # Отлов ивентов на удаление из бд
                for peer_id in self.events.delete_group:
                    self.__delete_group(peer_id)
                    self.events.delete_group.remove(peer_id)

            except:
                logger.exception('')

            # От перегрузки
            sleep(0.1)

    def run(self):
        logger.info("Запуск циклов")

        vk_bot_loop = Thread(target=self.bot.main_loop, daemon=True)
        vk_bot_loop.start()

        event_loop = Thread(target=self.event_loop)
        event_loop.start()

        parsing_loop = Thread(target=self.parsing_loop, daemon=True)
        parsing_loop.start()


if __name__ == '__main__':
    app = Main()
    try:
        app.run()
    except:
        logger.exception('')
