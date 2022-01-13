import sqlite3

import logger as log

logger = log.get_logger(__name__)


class DataBase:
    def __init__(self, database):
        self.db = database
        self.connection = sqlite3.connect(self.db)
        self.cursor = self.connection.cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS groups(
                               peer_id INT PRIMARY KEY,
                               name TEXT,
                               adv INT,
                               style_id INT);""")
        self.connection.commit()

    def reconnect(self):
        logger.info("Подключение к базе данных")
        self.connection = sqlite3.connect(self.db)
        self.cursor = self.connection.cursor()

    def add_group(self, peer_id, group_name, adv=1, style_id=0):
        self.cursor.execute("INSERT INTO groups VALUES(?, ?, ?, ?);", (peer_id, group_name, adv, style_id))
        self.connection.commit()
        logger.debug(f"Для {peer_id} создано group с name: {group_name}")

    def set_by_peer_id(self, peer_id, field, value):
        self.cursor.execute(f"UPDATE groups SET {field}=? WHERE peer_id=?;", (value, peer_id))
        self.connection.commit()
        logger.debug(f"Для {peer_id} установлено {field}: {value}")

    @staticmethod
    def __list_to_dict(user_info):
        return {'peer_id': user_info[0],
                'name': user_info[1],
                "adv": user_info[2],
                "style_id": user_info[3]}

    def get_by_peer_id(self, peer_id):
        self.cursor.execute("SELECT * from groups WHERE peer_id=?;", (peer_id,))
        result = [self.__list_to_dict(info) for info in self.cursor.fetchmany()]
        if result:
            return result[0]
        return result

    def get_adverted(self):
        self.cursor.execute("SELECT * from groups WHERE adv=1;")
        return [self.__list_to_dict(info) for info in self.cursor.fetchall()]

    def delete_by_peer_id(self, peer_id):
        self.cursor.execute(f"DELETE FROM groups WHERE peer_id=?;", (peer_id,))
        self.connection.commit()
        logger.debug(f"Информация о {peer_id} удалена")


if __name__ == '__main__':
    db = DataBase("database.db")
    db.cursor.execute("SELECT * FROM groups;")
    res = db.cursor.fetchall()
    for i in res:
        print(i)
