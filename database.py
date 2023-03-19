import sqlite3
from dataclasses import dataclass
from typing import Iterable

import logger as log

logger = log.get_logger(__name__)


@dataclass()
class UserInfo:
    user_id: str
    service_name: str

    groups: Iterable[str]

    adv: bool = True
    style_id: int = 0


INIT_SQL_CODE = """
CREATE TABLE IF NOT EXISTS Users
(
    user_id TEXT,
    service_name TEXT,
    
    adv INT,
    style_id INT,
    
    PRIMARY KEY (user_id, service_name)
);

CREATE TABLE IF NOT EXISTS UserGroups
(
    user_id TEXT,
    service_name TEXT,
    
    group_name TEXT,
    
    FOREIGN KEY (user_id, service_name)
    REFERENCES Users(user_id, service_name)
);
"""


class DataBase:
    def __init__(self, database, **connect_kwargs):
        self.db = database
        self.connection = sqlite3.connect(self.db, **connect_kwargs)
        self.cursor = self.connection.cursor()
        self.cursor.executescript(INIT_SQL_CODE)
        self.connection.commit()

    def reconnect(self, **connect_kwargs):
        logger.info("Подключение к базе данных")
        self.connection = sqlite3.connect(self.db, **connect_kwargs)
        self.cursor = self.connection.cursor()

    def get_user(self, user_id: str, service_name: str) -> UserInfo:
        self.cursor.execute(
            "SELECT user_id, service_name, adv, style_id FROM Users WHERE user_id=? AND service_name=?;",
            (user_id, service_name))
        user = self.cursor.fetchone()
        if not user:
            return user

        ser_id, service_name, adv, style_id = user

        self.cursor.execute(
            "SELECT group_name FROM UserGroups WHERE user_id=? AND service_name=?;",
            (user_id, service_name)
        )
        groups = sum(self.cursor.fetchall(), ())

        return UserInfo(
            user_id=user_id,
            service_name=service_name,
            groups=groups,
            adv=adv,
            style_id=style_id
        )

    def add_user(self, user_info: UserInfo):
        self.cursor.execute(
            "INSERT INTO Users('user_id', 'service_name', 'adv', 'style_id') VALUES(?, ?, ?, ?);",
            (user_info.user_id, user_info.service_name, user_info.adv, user_info.style_id)
        )
        for group_name in user_info.groups:
            self.cursor.execute(
                "INSERT INTO UserGroups('user_id', 'service_name', 'group_name') VALUES(?, ?, ?);",
                (user_info.user_id, user_info.service_name, group_name)
            )
        self.connection.commit()
        logger.debug(f"Создан пользователь {user_info.user_id} {user_info.service_name} {user_info.groups}")

    def delete_user(self, user_id: str, service_name: str):
        self.cursor.execute(
            "DELETE FROM Users WHERE user_id=? AND service_name=?;",
            (user_id, service_name)
        )
        self.cursor.execute(
            "DELETE FROM UserGroups WHERE user_id=? AND service_name=?;",
            (user_id, service_name)
        )

        self.connection.commit()
        logger.debug(f"Информация о {user_id} {service_name} удалена")

    def set_user_groups(self, user_id: str, service_name: str, groups: Iterable[str]):
        self.cursor.execute(
            "DELETE FROM UserGroups WHERE user_id=? AND service_name=?;",
            (user_id, service_name)
        )
        for group_name in groups:
            self.cursor.execute(
                "INSERT INTO UserGroups('user_id', 'service_name', 'group_name') VALUES(?, ?, ?);",
                (user_id, service_name, group_name)
            )

        self.connection.commit()
        logger.debug(f"Для пользователя {user_id} {service_name} установленно {groups=}")

    def set_user_adv(self, user_id: str, service_name: str, adv: bool):
        self.cursor.execute(
            "UPDATE Users SET adv=? WHERE user_id=? AND service_name=?;",
            (adv, user_id, service_name)
        )
        self.connection.commit()
        logger.debug(f"Для пользователя {user_id} {service_name} установленно {adv=}")

    def set_user_style(self, user_id: str, service_name: str, style_id):
        self.cursor.execute(
            "UPDATE Users SET style_id=? WHERE user_id=? AND service_name=?;",
            (style_id, user_id, service_name)
        )
        self.connection.commit()
        logger.debug(f"Для пользователя {user_id} {service_name} установленно {style_id=}")

    def get_adverted(self) -> list[UserInfo]:
        self.cursor.execute(
            "SELECT user_id, service_name, adv, style_id FROM Users WHERE adv=1;",
        )
        users = self.cursor.fetchall()
        return self.__users_to_userinfo(users)

    def get_all(self) -> list[UserInfo]:
        self.cursor.execute(
            "SELECT user_id, service_name, adv, style_id FROM Users;",
        )
        users = self.cursor.fetchall()
        return self.__users_to_userinfo(users)

    def __users_to_userinfo(self, users):
        users_info = []

        for (user_id, service_name, adv, style_id) in users:
            self.cursor.execute(
                "SELECT group_name FROM UserGroups WHERE user_id=? AND service_name=?;",
                (user_id, service_name)
            )
            user_groups = sum(self.cursor.fetchall(), ())

            users_info.append(
                UserInfo(
                    user_id=user_id,
                    service_name=service_name,
                    groups=user_groups,
                    adv=adv,
                    style_id=style_id
                )
            )
        return users_info


if __name__ == '__main__':
    logger = log.setup_applevel_logger()

    db = DataBase("database.db")

    users = db.get_all()
    for i in users:
        print(i)
