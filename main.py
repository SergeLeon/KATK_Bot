from threading import Thread
from time import sleep

from event import Event
import logger as log
import message_templates
from config import URL, CHECK_TIME
from data_parser import Parser, table_type
from database import DataBase
from table_formatter import table_to_str, tables_to_group_names, STYLES

logger = log.setup_applevel_logger()


class Main:
    def __init__(self):
        self.events = []
        self.services = {}
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

    def register_service(self, service, service_name: str, token, **kwargs):
        self.services[service_name] = service(service_name=service_name, token=token, events=self.events, **kwargs)

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
                            self.events.append(Event.SEND_TABLE(service_name=group_info["service_name"],
                                                                user_id=group_info["user_id"],
                                                                group_name=group_info["name"]))

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
                                self.events.append(Event.SEND_TABLE(service_name=group_info["service_name"],
                                                                    user_id=group_info["user_id"],
                                                                    group_name=group_info["name"]))
                else:
                    logger.warning("Парсер ничего не вернул")

            except:
                logger.exception('')

            sleep(CHECK_TIME)

    def service_send(self, service_name: str, user_id, message: str):
        self.services[service_name].send(user_id=user_id, message=message)

    def _find_group_name(self, finding_group: str) -> str:
        for group in self.group_names:
            if finding_group in group:
                return group
        return ""

    def _find_group_table(self, group_name: str) -> table_type:
        for table in self.tables:
            if table[0][1] == group_name:
                return table

    def _service_send_table(self, user_id, service_name: str, group_name: str, style_id: int):
        self.service_send(service_name=service_name, user_id=user_id,
                          message=table_to_str(
                              table=self._find_group_table(group_name),
                              style_id=style_id,
                              date=self.pars.get_date(),
                              consider_column_width=False))

    def __set_group(self, user_id, service_name: str, group_name):
        norm_group = self._find_group_name(group_name)
        if bool(norm_group):

            if self.db.get_user(user_id, service_name):
                self.db.set_by_user_id(user_id=user_id, service_name=service_name, field="name", value=norm_group)
            else:
                self.db.add_group(user_id=user_id, group_name=norm_group, service_name=service_name)

            self.service_send(service_name=service_name, user_id=user_id,
                              message=message_templates.GROUP_CHANGED_TO.format(group=norm_group))

        else:
            self.service_send(service_name=service_name, user_id=user_id,
                              message=message_templates.GROUP_NOT_FOUND.format(group=group_name))

    def __set_style(self, user_id, service_name: str, style_id):
        if style_id.isnumeric() and (int(style_id) in STYLES):
            style_id = int(style_id)

            if self.db.get_user(user_id, service_name):
                self.db.set_by_user_id(user_id=user_id, service_name=service_name, field="style_id", value=style_id)
                self.service_send(service_name=service_name, user_id=user_id,
                                  message=message_templates.STYLE_CHANGED_TO.format(style=style_id))
            else:
                self.service_send(service_name=service_name, user_id=user_id,
                                  message=message_templates.NEED_SELECT_GROUP)
        else:
            self.service_send(service_name=service_name, user_id=user_id,
                              message=message_templates.STYLE_NOT_FOUND.format(style=style_id))

    def __set_adv(self, user_id, service_name: str):
        group_info = self.db.get_user(user_id, service_name)
        if group_info:
            group_adv = not group_info["adv"]
            self.db.set_by_user_id(user_id=user_id, service_name=service_name, field="adv", value=group_adv)

            if group_adv:
                self.service_send(service_name=service_name, user_id=user_id, message=message_templates.ADVERTS_ON)
            else:
                self.service_send(service_name=service_name, user_id=user_id, message=message_templates.ADVERTS_OFF)
        else:
            self.service_send(service_name=service_name, user_id=user_id, message=message_templates.NEED_SELECT_GROUP)

    def _send_table_by_db(self, user_id, service_name: str):
        group_info = self.db.get_user(user_id, service_name)
        if group_info:
            if group_info["name"] in self.group_names:
                self._service_send_table(user_id=group_info["user_id"],
                                         service_name=service_name,
                                         group_name=group_info["name"],
                                         style_id=group_info["style_id"])
            else:
                self.service_send(service_name=service_name, user_id=user_id,
                                  message=f"{message_templates.GROUP_NOT_FOUND.format(group=group_info['name'])}\n"
                                          f"{message_templates.NEED_SELECT_GROUP}")
        else:
            self.service_send(service_name=service_name, user_id=user_id, message=message_templates.NEED_SELECT_GROUP)

    def _send_table_by_group_name(self, user_id, service_name: str, group_name: str = None):
        norm_group = self._find_group_name(group_name)
        if bool(norm_group):
            group_info = self.db.get_user(user_id, service_name)
            style_id = group_info["style_id"] if group_info else 0
            self._service_send_table(user_id=user_id,
                                     service_name=service_name,
                                     group_name=norm_group,
                                     style_id=style_id)
        else:
            self.service_send(service_name=service_name, user_id=user_id,
                              message=message_templates.GROUP_NOT_FOUND.format(group=group_name))

    def __send_table(self, user_id, service_name: str, group_name: str = None):
        if self.tables and self.group_names:
            if group_name is None:
                self._send_table_by_db(user_id=user_id, service_name=service_name)
            else:
                self._send_table_by_group_name(user_id=user_id, service_name=service_name, group_name=group_name)
        else:
            self.service_send(service_name=service_name, user_id=user_id, message=message_templates.NO_INFORMATION)

    def __delete_group(self, user_id, service_name: str):
        self.db.delete_user(user_id=user_id, service_name=service_name)

    def event_loop(self):
        logger.info("event_loop запущен")
        while True:
            try:
                for event in self.events:
                    if event.service_name not in self.services:
                        logger.warning(f'Сервис {event.service} имеется в базе но не зарегистрирован в приложении.')
                    else:
                        event_type = type(event)

                        if event_type == Event.SET_GROUP:
                            self.__set_group(
                                user_id=event.user_id,
                                service_name=event.service_name,
                                group_name=event.group_name)

                        elif event_type == Event.SET_STYLE:
                            self.__set_style(
                                user_id=event.user_id,
                                service_name=event.service_name,
                                style_id=event.style_id)

                        elif event_type == Event.SET_ADV:
                            self.__set_adv(
                                user_id=event.user_id,
                                service_name=event.service_name)

                        elif event_type == Event.SEND_TABLE:
                            self.__send_table(
                                user_id=event.user_id,
                                group_name=event.group_name,
                                service_name=event.service_name)

                        elif event_type == Event.DELETE_GROUP:
                            self.__delete_group(
                                user_id=event.user_id,
                                service_name=event.service_name)
                        else:
                            logger.warning(f"Неотлавливаемый event: {event}")

                    self.events.remove(event)
            except:
                logger.exception('')

            # От перегрузки
            sleep(0.1)

    def run(self):
        logger.info("Запуск циклов")

        for _, service in self.services.items():
            service_loop = Thread(target=service.main_loop, daemon=True)
            service_loop.start()

        event_loop = Thread(target=self.event_loop)
        event_loop.start()

        parsing_loop = Thread(target=self.parsing_loop, daemon=True)
        parsing_loop.start()


def register_all_services(application: Main):
    from vk_bot import VKBot
    from config import VK_TOKEN
    application.register_service(service=VKBot, service_name="vk", token=VK_TOKEN)


if __name__ == '__main__':
    app = Main()
    try:
        register_all_services(app)
        app.run()
    except:
        logger.exception('')
