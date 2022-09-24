"""
Система событий основанная на namedtuple.

Все события должны иметь поля от Event.
Тип события определяется по его классу.

Обязательные поля:
    service - Наименование сервиса взаимодействия с пользователем (vk, telegram)
    user_id - Идентификатор пользователя
"""
from collections import namedtuple

BaseEvent = namedtuple('BaseEvent', ['service', 'user_id'])

SetGroupEvent = namedtuple('SetGroupEvent', BaseEvent._fields + ('group_name',))

SetStyleEvent = namedtuple('SetStyleEvent', BaseEvent._fields + ('style_id',))

SetAdvEvent = namedtuple('SetAdvEvent', BaseEvent._fields)

SendTableEvent = namedtuple('SendTableEvent', BaseEvent._fields)

DeleteGroupEvent = namedtuple('DeleteGroupEvent', BaseEvent._fields)


class Event:
    SET_GROUP = SetGroupEvent
    SET_STYLE = SetStyleEvent
    SET_ADV = SetAdvEvent

    SEND_TABLE = SendTableEvent

    DELETE_GROUP = DeleteGroupEvent
