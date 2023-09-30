"""Тексты ответов на сообщения"""
from config import VERSION

BOT_ADD_EVENT = """
Для использования бота необходимо следовать руководству пользователя:
vk.com/@-209119751-rukovodstvo-polzovatelya"""

HELP_COMMAND = """
/sl help - вывод всех доступных команд.
/sl group <имя_группы> - установить группу (затирает другие).
/sl group add <имя_группы> - добавить группу к отслеживанию.
/sl table - вывести расписание.
/sl advert - вкл/выкл оповещения.
/sl info - информация о боте.

Пример команды:
/sl group 20-ТО-1"""

INFO_COMMAND = f""" Расписание КАТК44 | Бот предназначен для оповещения об обновлении \
или изменении расписания выбранной пользователем группы в учебном расписании Костромского автотранспортного колледжа. 

Бот в VK:
https://vk.com/katk44bot

Бот в Telegram:
https://t.me/KATK44bot

Актуальная версия: {VERSION}"""

UNKNOWN_COMMAND = """
Команда не распознана, для помощи наберите
/sl help"""

GROUP_CHANGED_TO = "Группа изменена на {group}."

GROUP_NOT_FOUND = "Группа {group} не найдена."

GROUP_ALREADY_TRACKED = "Группа {group} уже отслеживается."

GROUP_NOT_TRACKING = "Группа {group} не отслеживается."

GROUP_ADDED_TO_TRACKING = "Группа {group} добавлена к отслеживанию."

GROUP_REMOVED_FROM_TRACKING = "Группа {group} удалена из отслеживания."

GROUPS_ARE_EMPTY = "Список отслеживаемых групп пуст."

STYLE_CHANGED_TO = "Стиль изменен на: {style}"

STYLE_NOT_FOUND = "Стиль {style} не найден."

NEED_SELECT_GROUP = "Необходимо задать группу используя\n" \
                    "/sl group имя_группы"

ADVERTS_ON = "Оповещения включены."

ADVERTS_OFF = "Оповещения отключены."

NO_INFORMATION = "Информация отсутствует"

TABLE_FOR_DATE_NOT_FOUND = "Расписание на {date} для группы {group} не найдено."
