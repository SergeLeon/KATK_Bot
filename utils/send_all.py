import sys
from pathlib import Path

# Для возможности вызова напрямую
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from main import *


def send_all(app: Main = None):
    if app is None:
        app = Main()
        register_all_services(app)
        event_loop = Thread(target=app.event_loop)
        event_loop.start()
    tables = app.pars.get_tables()
    if tables:
        app.update()
        logger.info("Принудительная отправка таблиц")
        app._send_all()

    else:
        logger.warning("Парсер ничего не вернул")


if __name__ == "__main__":
    confirm = input("send all? (Yes/No):") == "Yes"
    if confirm:
        send_all()
