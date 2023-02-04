import time
from collections import Counter

import sys
from pathlib import Path

# Для возможности вызова напрямую
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from config import URL, REGULAR_TIMETABLE_PATH
from table_formatter import table_to_str
from parsers import Parser


def main():
    start_time = time.perf_counter()

    pars = Parser(URL, REGULAR_TIMETABLE_PATH)
    table_dict = pars.get_tables()

    for key, tabls in table_dict.items():
        print(key)
        for tabl in tabls.values():
            print(table_to_str(table=tabl,
                               style_id=0,
                               date=key,
                               consider_column_width=True))

        names = tabls.keys()

        c = Counter(sorted(names, key=lambda name: name[::-1]))
        print(len(names), len(c), c)

    print("--- %s seconds ---" % (time.perf_counter() - start_time))


if __name__ == "__main__":
    main()
