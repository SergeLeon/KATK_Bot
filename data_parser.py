from typing import Iterable
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup as bs
from bs4.element import Tag
from fake_useragent import UserAgent
from requests.exceptions import ReadTimeout, ConnectionError
from time import sleep

WEEKDAYS = ("понедельник", 'вторник', 'среда', 'четверг', 'пятница', 'суббота')
NUMBERS = "0123456789"

table_type = list[list[str]]


def _find_inclusion(string: str, inclusions: Iterable[str]) -> str:
    """
    Возвращает первое найденное в строке включение или пустую строку, если включений не найдено.
    """
    for inclusion in inclusions:
        if inclusion in string:
            return inclusion
    return ""


def _clear_str(string: str) -> str:
    string = string.replace("\n", " ")
    string = string.replace(u"\xa0", "")

    while "  " in string:
        string = string.replace("  ", " ")

    string = string.strip()

    return string


def _get_link(a: Tag, domain: str) -> str:
    link = a.get("href")
    if "http" not in link:
        link = f"http://{domain}{link}"
    return link


class Parser:
    def __init__(self, url: str):
        self.ua = UserAgent()
        self.url = url
        self.domain = urlparse(self.url).netloc
        self.session = requests.Session()
        self.soup = bs()
        self.date = ""
        self.update()

    def update(self, recon_max: int = 5, recon_time: int = 60, count: int = 1):
        try:
            self.session.headers.update({'User-Agent': self.ua.random})
            response = self.session.get(self.url, timeout=5).content
            self.soup = bs(response, "html.parser")
            self._update_date()

        except (ReadTimeout, ConnectionError):
            count += 1

            if count % (recon_max * 4) == 0:
                sleep(recon_time * 120)
            elif count % (recon_max * 2) == 0:
                sleep(recon_time * 10)
            elif count % recon_max == 0:
                sleep(recon_time)

            sleep(recon_time // 10)
            self.update(recon_max=recon_max, recon_time=recon_time, count=count)

    def _update_date(self):
        strings = self._pars_spans_text()
        for string in strings:
            string = string.lower()

            day = _find_inclusion(string, WEEKDAYS)
            if day:
                texts_words = string.split()
                date = ""

                # Отделение строк с информацией
                for word in texts_words:
                    if day in word or _find_inclusion(word, NUMBERS):
                        date += word

                self.date = date.title()
                break

    def get_date(self) -> str:
        return self.date

    def _get_cell_text(self, cell: Tag) -> str:
        text = cell.text.upper()

        text = _clear_str(text)

        text = text.replace(
            "ЭТОТ АДРЕС ЭЛЕКТРОННОЙ ПОЧТЫ ЗАЩИЩЕН ОТ СПАМ-БОТОВ. У ВАС ДОЛЖЕН БЫТЬ ВКЛЮЧЕН JAVASCRIPT ДЛЯ ПРОСМОТРА.",
            "ПОЧТА НА САЙТЕ.")

        # Поиск и вставка ссылки/ок
        cell_a = cell.find_all("a")
        if cell_a:
            for a in cell_a:
                link = _get_link(a=a, domain=self.domain)
                text += " " + link

        return text

    def _pars_today_tables(self) -> table_type:
        tables = self.soup.find_all("table")

        text_lines = []
        for table in tables:
            lines = table.find_all("tr")

            for line in lines:
                cells = line.find_all("td")

                texts = [self._get_cell_text(cell) for cell in cells]

                if any(texts):
                    text_lines.append(texts)

        return text_lines

    @staticmethod
    def _split_table_by_lines(text_table: table_type) -> list[table_type]:
        last_line = 0
        new_tables = []
        for line_num, line in enumerate(text_table):
            if "ГРУППА" in line[0]:
                new_tables.append(text_table[last_line: line_num])
                last_line = line_num
        new_tables.append(text_table[last_line: -1])

        return new_tables[1:]

    @staticmethod
    def _split_tables_by_columns(tables: list[table_type]) -> list[table_type]:
        group_tables = []
        for table in tables:

            for group_num in range(1, len(table[0])):
                group_tables.append([[line[0], line[group_num]] for line in table])

        return group_tables

    def _split_table(self, table: table_type) -> list[table_type]:
        return self._split_tables_by_columns(
            self._split_table_by_lines(table))

    @staticmethod
    def _delete_uninformative_table_lines(table: table_type) -> table_type:
        table = [[cell for cell in line] for line in table]

        for line in table[::-1]:
            if not line[1]:
                table.remove(line)
            else:
                break
        return table

    @staticmethod
    def _reformat_table(table: table_type) -> table_type:
        table = [[cell for cell in line] for line in table]

        for line in table:

            if len(line) == 2:
                titles = []
                additions = []
                if "http" in line[1]:
                    splited = line[1].split()

                    for word in splited:
                        if "http" in word:
                            additions.append(word)
                        else:
                            titles.append(word.strip())

                    line[1] = " ".join(titles)

                if "КАБ" in line[1]:
                    splited = line[1].split('КАБ')

                    title = splited[0].replace("(", "").strip()
                    cabinet_number = splited[1].replace(")", "").replace(".", "").strip()

                    line[1] = title
                    additions.insert(0, cabinet_number)

                line.append(" ".join(additions))

        # если в клетке названия группы есть что-то, кроме группы оно переносится в другую колонку.
        table[0][1] = table[0][1].replace(' ', "")
        first_line = table[0][1].split(" ")
        table[0][1] = first_line[0]
        if len(first_line) > 1:
            table[0][2] += f' {first_line[1]}'

        return table

    def _tables_to_group_tables(self, tables: list[table_type]) -> list[table_type]:
        group_tables = []

        for table in tables:
            table = self._delete_uninformative_table_lines(table)
            if table:
                table = self._reformat_table(table)

                group_tables.append(table)

        return self._delete_duplicates(group_tables)

    @staticmethod
    def _delete_duplicates(tables: list[table_type]) -> list[table_type]:
        group_tables = []
        groups = []

        for num, table in enumerate(tables):
            if num == len(tables) - 1:
                num -= 1
            if table[0][1] in groups and tables[num + 1][0][1] in groups:
                break

            groups.append(table[0][1])
            group_tables.append(table)

        return group_tables

    def get_tables(self) -> list[table_type]:
        return self._tables_to_group_tables(
               self._split_table(
               self._pars_today_tables()))

    def _pars_spans_text(self) -> list:
        spans = self.soup.find_all("b")
        spans_text = [span.text for span in spans]
        return spans_text


if __name__ == '__main__':
    import time
    from config import URL
    from table_formatter import table_to_str, tables_to_group_names

    start_time = time.time()

    pars = Parser(URL)
    tabls = pars.get_tables()
    for tabl in tabls:
        print(table_to_str(table=tabl,
                           style_id=0,
                           date=pars.get_date(),
                           consider_column_width=True))

    names = tables_to_group_names(tabls)
    print(len(names), names)

    print("--- %s seconds ---" % (time.time() - start_time))
