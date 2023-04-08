import sys
from collections import Counter
from pathlib import Path

# Для возможности вызова напрямую
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from database import DataBase


def main():
    db = DataBase(Path(__file__).parent.parent / "database.db")

    users = db.get_all()
    groups = []
    for i in users:
        print(i)
        groups.extend(i.groups)

    c = Counter(groups)
    print(len(users), len(c), c)


if __name__ == "__main__":
    main()
