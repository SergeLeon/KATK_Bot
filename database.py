import sqlite3

import logger as log

logger = log.get_logger(__name__)


class DataBase:
    def __init__(self, database, **connect_kwargs):
        self.db = database
        self.connection = sqlite3.connect(self.db, **connect_kwargs)
        self.cursor = self.connection.cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS groups(
                               user_id TEXT,
                               name TEXT,
                               adv INT,
                               style_id INT,
                               service_name TEXT);""")
        self.connection.commit()

    def reconnect(self, **connect_kwargs):
        logger.info("Подключение к базе данных")
        self.connection = sqlite3.connect(self.db, **connect_kwargs)
        self.cursor = self.connection.cursor()

    def add_group(self, user_id, service_name: str, group_name: str, adv: int = 1, style_id: int = 0):
        self.cursor.execute("INSERT INTO groups VALUES(?, ?, ?, ?, ?);",
                            (user_id, group_name, adv, style_id, service_name))
        self.connection.commit()
        logger.debug(f"Для {user_id} {service_name} создано group с name: {group_name}")

    def set_by_user_id(self, user_id, service_name: str, field: str, value):
        self.cursor.execute(f"UPDATE groups SET {field}=? WHERE user_id=? AND service_name=?;",
                            (value, user_id, service_name))
        self.connection.commit()
        logger.debug(f"Для {user_id} {service_name} установлено {field}: {value}")

    @staticmethod
    def _list_to_dict(user_info):
        return {'user_id': user_info[0],
                'name': user_info[1],
                "adv": user_info[2],
                "style_id": user_info[3],
                "service_name": user_info[4]}

    def get_user(self, user_id, service_name: str):
        self.cursor.execute("SELECT * from groups WHERE user_id=? AND service_name=?;",
                            (user_id, service_name))
        result = self.cursor.fetchone()
        if result:
            return self._list_to_dict(result)
        return result

    def get_adverted(self):
        self.cursor.execute("SELECT * from groups WHERE adv=1;")
        return [self._list_to_dict(info) for info in self.cursor.fetchall()]

    def delete_user(self, user_id, service_name: str):
        self.cursor.execute(f"DELETE FROM groups WHERE user_id=? AND service_name=?;",
                            (user_id, service_name))
        self.connection.commit()
        logger.debug(f"Информация о {user_id} {service_name} удалена")


if __name__ == '__main__':
    db = DataBase("database.db")
    db.cursor.execute("SELECT * FROM groups;")
    res = db.cursor.fetchall()
    b = set()
    for i in res:
        info = db._list_to_dict(i)
        b.add(info["name"])
        print(info)
    print(len(b), sorted(list(b)))
