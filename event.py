"""
Система событий основанная на dataclass.

Все события наследуются от BaseEvent.
Тип события определяется по его классу.

Обязательные поля:
    service_name - Наименование сервиса взаимодействия с пользователем (vk, telegram)
    user_id - Идентификатор пользователя
"""
from dataclasses import dataclass
from typing import Iterable, Union


@dataclass(frozen=True)
class BaseEvent:
    service_name: str
    user_id: str


@dataclass(frozen=True)
class SetGroupEvent(BaseEvent):
    group_name: str


@dataclass(frozen=True)
class AddGroupEvent(BaseEvent):
    group_name: str


@dataclass(frozen=True)
class DelGroupEvent(BaseEvent):
    group_name: str


@dataclass(frozen=True)
class SetStyleEvent(BaseEvent):
    style_id: str


@dataclass(frozen=True)
class SetAdvEvent(BaseEvent):
    pass


@dataclass(frozen=True)
class SendTableEvent(BaseEvent):
    groups: Union[Iterable[str], None]


@dataclass(frozen=True)
class DeleteUserEvent(BaseEvent):
    pass


class Event:
    SET_GROUP = SetGroupEvent
    ADD_GROUP = AddGroupEvent
    DEL_GROUP = DelGroupEvent

    SET_STYLE = SetStyleEvent
    SET_ADV = SetAdvEvent

    SEND_TABLE = SendTableEvent

    DELETE_USER = DeleteUserEvent
