from threading import Thread
from time import sleep

from event import Event
import logger as log
import message_templates
from config import URL, CHECK_TIME, REGULAR_TIMETABLE_PATH, table_dict_type
from parsers import Parser
from database import DataBase, UserInfo
from table_formatter import table_to_str, tables_dict_to_group_names, prepare_group_name, STYLES

logger = log.setup_applevel_logger()


class Main:
    def __init__(self):
        self.events = []
        self.services = {}
        self.pars = Parser(URL, REGULAR_TIMETABLE_PATH)
        # хранит расписание
        self.tables_dict: table_dict_type = {}
        # хранит названия групп
        self.group_names: list[str] = []
        # хранит дату
        self.tables_date: str = ""
        self.update()

        # check_same_thread отключен т.к. только event_loop пишет в базу.
        self.db = DataBase("database.db", check_same_thread=False)

        logger.info("Приложение инициализировано")

    def register_service(self, service, service_name: str, token, **kwargs):
        self.services[service_name] = service(
            service_name=service_name,
            token=token,
            events=self.events,
            **kwargs
        )
        logger.debug(f"Зарегистрирован сервис {service_name}:{service}")

    def update(self):
        self.tables_dict = self.pars.get_tables()
        self.group_names = tables_dict_to_group_names(self.tables_dict)
        self.tables_date = self.pars.get_date()

    def __parsing_cycle(self) -> None:
        self.pars.update()

        old_tables_dict = self.tables_dict
        new_tables_dict = self.pars.get_tables()
        # Проверка на существование информации
        if not new_tables_dict:
            logger.warning("Парсер ничего не вернул")
            return

        if not self._check_group_count(new_tables_dict):
            logger.warning(f"Разное кол-во групп в расписании; {self._represent_tables(new_tables_dict)}")

        # Если обновлена дата или в новых таблицах имеется дата отличающаяся от имеющихся в старых
        if (self.pars.get_date() != self.tables_date) or (set(new_tables_dict) - set(old_tables_dict)):
            logger.info("Все таблицы обновлены")
            logger.debug(self._represent_tables(new_tables_dict))

            self._send_all()
            return
        # Если удалено расписание на прошлый день, то сообщения не присылаются
        if len(old_tables_dict) != len(new_tables_dict):

            deleted_dates = set(old_tables_dict) ^ set(new_tables_dict)

            # Удаление лишних дат для последующего сравнения
            for date in deleted_dates:
                old_tables_dict.pop(date)

            logger.info(f"Удалено расписание на: {'; '.join(deleted_dates)}")

        if updated_groups := self._find_difference(new_tables_dict, old_tables_dict):
            logger.info(f"Таблицы обновлены: {len(updated_groups)};")
            logger.debug(f"для {updated_groups}")

            self._send_updated(updated_groups)

    @staticmethod
    def _represent_tables(tables_dict):
        return "; ".join(f'{date}:{len(tables)}' for date, tables in tables_dict.items())

    @staticmethod
    def _check_group_count(tables_dict):
        if len(tables_dict) <= 1:
            return True
        tables_count_list = [len(tables) for tables in tables_dict.values()]
        return all(tables_count == tables_count_list[0] for tables_count in tables_count_list[1:])

    def _send_all(self):
        self.update()
        for user_info in self.db.get_adverted():
            if not user_info.groups:
                continue

            self.events.append(
                Event.SEND_TABLE(
                    service_name=user_info.service_name,
                    user_id=user_info.user_id,
                    groups=user_info.groups
                )
            )

    def _send_updated(self, updated_groups):
        self.update()
        for user_info in self.db.get_adverted():
            updated_user_groups = [user_group for user_group in user_info.groups if user_group in updated_groups]
            if updated_user_groups:
                self.events.append(
                    Event.SEND_TABLE(
                        service_name=user_info.service_name,
                        user_id=user_info.user_id,
                        groups=updated_user_groups
                    )
                )

    @staticmethod
    def _find_difference(old_tables_dict: table_dict_type, new_tables_dict: table_dict_type) -> list[str]:
        updated_groups = set()
        for new_tables, old_tables in zip(new_tables_dict.values(), old_tables_dict.values()):
            new_tables = list(new_tables.values())
            old_tables = list(old_tables.values())

            new_tables.sort(key=lambda table: table[0][1])
            old_tables.sort(key=lambda table: table[0][1])

            for new_table, old_table in zip(new_tables, old_tables):
                if new_table != old_table:
                    updated_groups.add(new_table[0][1])

        return list(updated_groups)

    def parsing_loop(self):
        self.update()

        logger.info("parsing_loop запущен")
        while True:
            try:
                self.__parsing_cycle()
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

    def _service_send_tables(self, user_id, service_name: str, groups: list[str], style_id: int):
        message = ""
        for group_name in groups:
            message += self.__get_table(group_name, style_id)

        message = message.strip()
        self.service_send(
            service_name=service_name,
            user_id=user_id,
            message=message
        )

    def __get_table(self, group_name, style_id):
        message = ""
        for date, tables in self.tables_dict.items():
            table = tables.get(group_name)
            if not table:
                message += message_templates.TABLE_FOR_DATE_NOT_FOUND.format(date=date, group=group_name)
                message += "\n"
            else:
                message += table_to_str(
                    table=tables.get(group_name),
                    style_id=style_id,
                    date=date,
                    consider_column_width=False
                )
            message += "\n"
        return message

    def __set_group(self, user_id, service_name: str, group_name):
        normalized_group = prepare_group_name(group_name)
        normalized_group = self._find_group_name(normalized_group)
        if not normalized_group:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.GROUP_NOT_FOUND.format(group=group_name)
            )
            return

        if self.db.get_user(user_id, service_name):
            self.db.set_user_groups(
                user_id=user_id,
                service_name=service_name,
                groups=(normalized_group,)
            )
        else:
            self.db.add_user(
                UserInfo(
                    user_id=user_id,
                    service_name=service_name,
                    groups=(normalized_group,),
                )
            )
        self.service_send(
            service_name=service_name,
            user_id=user_id,
            message=message_templates.GROUP_CHANGED_TO.format(group=normalized_group)
        )

    def __add_group(self, user_id, service_name: str, group_name):
        normalized_group = prepare_group_name(group_name)
        normalized_group = self._find_group_name(normalized_group)
        if not normalized_group:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.GROUP_NOT_FOUND.format(group=group_name)
            )
            return

        user_info = self.db.get_user(user_id, service_name)
        if not user_info:
            self.db.add_user(
                UserInfo(
                    user_id=user_id,
                    service_name=service_name,
                    groups=(normalized_group,),
                )
            )
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.GROUP_CHANGED_TO.format(group=normalized_group)
            )
            return

        if normalized_group in user_info.groups:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.GROUP_ALREADY_TRACKED.format(group=normalized_group)
            )
            return

        self.db.set_user_groups(
            user_id=user_id,
            service_name=service_name,
            groups=(*user_info.groups, normalized_group)
        )

        self.service_send(
            service_name=service_name,
            user_id=user_id,
            message=message_templates.GROUP_ADDED_TO_TRACKING.format(
                group=normalized_group,
                groups=", ".join((*user_info.groups, normalized_group))
            )
        )

    def __del_group(self, user_id, service_name: str, group_name):
        normalized_group = prepare_group_name(group_name)
        normalized_group = self._find_group_name(normalized_group)
        if not normalized_group:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.GROUP_NOT_FOUND.format(group=group_name)
            )
            return

        user_info = self.db.get_user(user_id, service_name)
        if not user_info or not user_info.groups:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.GROUPS_ARE_EMPTY
            )
            return

        if normalized_group not in user_info.groups:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.GROUP_NOT_TRACKING.format(group=normalized_group)
            )
            return

        new_groups = list(user_info.groups)
        new_groups.remove(normalized_group)

        self.db.set_user_groups(
            user_id=user_id,
            service_name=service_name,
            groups=new_groups
        )

        self.service_send(
            service_name=service_name,
            user_id=user_id,
            message=message_templates.GROUP_REMOVED_FROM_TRACKING.format(group=normalized_group)
        )

    def __set_style(self, user_id, service_name: str, style_id):
        style_id_is_valid = style_id.isnumeric() and (int(style_id) in STYLES)

        if not style_id_is_valid:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.STYLE_NOT_FOUND.format(style=style_id)
            )
            return

        style_id = int(style_id)

        if self.db.get_user(user_id, service_name):
            self.db.set_user_style(
                user_id=user_id,
                service_name=service_name,
                style_id=style_id
            )
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.STYLE_CHANGED_TO.format(style=style_id)
            )
        else:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.NEED_SELECT_GROUP
            )

    def __set_adv(self, user_id, service_name: str):
        user_info = self.db.get_user(user_id, service_name)
        if not user_info:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.NEED_SELECT_GROUP
            )
            return

        user_adv = not user_info.adv
        self.db.set_user_adv(
            user_id=user_id,
            service_name=service_name,
            adv=user_adv
        )

        self.service_send(
            service_name=service_name,
            user_id=user_id,
            message=message_templates.ADVERTS_ON if user_adv else message_templates.ADVERTS_OFF
        )

    def _send_table_by_db(self, user_id, service_name: str):
        user_info = self.db.get_user(user_id, service_name)
        if not user_info or not user_info.groups:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.NEED_SELECT_GROUP
            )
            return

        self._service_send_tables(
            user_id=user_id,
            service_name=service_name,
            groups=user_info.groups,
            style_id=user_info.style_id
        )

    def _send_table_by_groups(self, user_id, service_name: str, groups: list):
        user_info = self.db.get_user(user_id, service_name)
        style_id = user_info.style_id if user_info else 0
        self._service_send_tables(
            user_id=user_id,
            service_name=service_name,
            groups=groups,
            style_id=style_id
        )

    def __send_table(self, user_id, service_name: str, groups: list = None):
        if not self.tables_dict:
            self.service_send(
                service_name=service_name,
                user_id=user_id,
                message=message_templates.NO_INFORMATION
            )
            return

        if groups is None:
            self._send_table_by_db(user_id=user_id, service_name=service_name)
        else:
            self._send_table_by_groups(
                user_id=user_id,
                service_name=service_name,
                groups=groups
            )

    def __delete_group(self, user_id, service_name: str):
        self.db.delete_user(user_id=user_id, service_name=service_name)

    def __change_user_id(self, user_id: str, service_name:str, new_user_id: str):
        user_info = self.db.get_user(new_user_id, service_name)
        if not user_info:
            self.db.change_user_id(user_id=user_id, service_name=service_name, new_user_id=new_user_id)
        else:
            self.db.set_user_adv(
                user_id=user_id,
                service_name=service_name,
                adv=False
            )

    def __handle_event(self, event) -> None:
        if event.service_name not in self.services:
            logger.warning(
                f'Сервис {event.service_name} имеется в базе но не зарегистрирован в приложении.')
            return

        event_type = type(event)

        if event_type == Event.SET_GROUP:
            self.__set_group(
                user_id=event.user_id,
                service_name=event.service_name,
                group_name=event.group_name
            )

        elif event_type == Event.ADD_GROUP:
            self.__add_group(
                user_id=event.user_id,
                service_name=event.service_name,
                group_name=event.group_name
            )

        elif event_type == Event.DEL_GROUP:
            self.__del_group(
                user_id=event.user_id,
                service_name=event.service_name,
                group_name=event.group_name
            )

        elif event_type == Event.SET_STYLE:
            self.__set_style(
                user_id=event.user_id,
                service_name=event.service_name,
                style_id=event.style_id
            )

        elif event_type == Event.SET_ADV:
            self.__set_adv(
                user_id=event.user_id,
                service_name=event.service_name
            )

        elif event_type == Event.SEND_TABLE:
            self.__send_table(
                user_id=event.user_id,
                groups=event.groups,
                service_name=event.service_name
            )

        elif event_type == Event.DELETE_USER:
            self.__delete_group(
                user_id=event.user_id,
                service_name=event.service_name
            )
        elif event_type == Event.CHANGE_ID:
            self.__change_user_id(
                user_id=event.user_id,
                service_name=event.service_name,
                new_user_id=event.new_user_id
            )
        else:
            logger.warning(f"Неотлавливаемый event: {event}")

    def event_loop(self):
        logger.info("event_loop запущен")
        while True:
            try:
                for event in self.events:
                    self.__handle_event(event)

                    self.events.remove(event)
            except:
                logger.exception('')

            # От перегрузки
            sleep(0.1)

    def run(self):
        logger.info("Запуск циклов")

        assert self.services, "Отсутствуют сервисы для запуска"

        for _, service in self.services.items():
            service_loop = Thread(target=service.main_loop, daemon=True)
            service_loop.start()

        event_loop = Thread(target=self.event_loop)
        event_loop.start()

        parsing_loop = Thread(target=self.parsing_loop, daemon=True)
        parsing_loop.start()


def register_all_services(application: Main):
    import bots
    import config

    if config.VK_TOKEN:
        application.register_service(
            service=bots.VKBot,
            service_name="vk",
            token=config.VK_TOKEN
        )

    if config.TELEGRAM_TOKEN:
        application.register_service(
            service=bots.TelegramBot,
            service_name="telegram",
            token=config.TELEGRAM_TOKEN
        )


if __name__ == '__main__':
    app = Main()
    try:
        register_all_services(app)
        app.run()
    except:
        logger.exception('')
