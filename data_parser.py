from time import sleep

import requests
from bs4 import BeautifulSoup as bs


class Parser:
    def __init__(self, url):
        self.url = url
        self.soup = bs()
        self.date = ""
        self.update()

    def update(self, recon_max=5, recon_time=60, count=1):
        try:
            self.soup = bs(requests.get(self.url).content, "html.parser")
            self._update_date()
        except:
            count += 1
            if count % (recon_max*2) == 0:
                sleep(recon_time*120)
            elif count % recon_max == 0:
                sleep(recon_time)

            sleep(recon_time // 10)
            self.update(count=count)

    def _update_date(self):
        date = self.__pars_spans_text()
        if date:
            date = date[0]
            date = ' '.join(date.split()[-3:]).title()
        else:
            date = ""
        self.date = date

    def get_today_date(self):
        return self.date

    def tables_to_group_names(self, tables):
        return [table[0][1] for table in tables]

    def __pars_today_tables(self):
        output = []
        tables = self.soup.find_all("table")
        groups = []
        for table in tables:
            lines = table.find_all("tr")

            text_table = []
            for line in lines:
                cells = line.find_all("td")

                texts = []
                for cell in cells:
                    # Привод значений в понятный вид
                    text = cell.text
                    text = text.strip("\n")
                    text = text.replace("\n", " ")
                    text = text.replace(u"\xa0", "")
                    text = text.strip()
                    texts.append(text.upper())

                if texts[1] in groups:
                    break
                else:
                    if not (texts.count("") == len(texts) or texts.count([]) == len(texts)):
                        text = texts[1]
                        if "ГРУППА" in text:
                            groups.append(text)
                        text_table.append(texts)

            output.append(text_table)

        # костыль бага с неполным списком в __text_tables_to_tables
        if output:
            output[-1].append(["", "ГРУППА"])

        return output

    @staticmethod
    def __text_tables_to_tables(text_tables):
        tables = []
        for table in text_tables:
            for line in table:
                tables.append(line)

        last_line = 0
        new_tables = []
        for line_num, line in enumerate(tables):
            if "ГРУППА" in line[1]:
                new_tables.append(tables[last_line: line_num])
                last_line = line_num
        return new_tables[1:]

    @staticmethod
    def __tables_to_group_tables(tables):
        group_tables = []
        for table in tables:

            group_count = 0
            for cell in table[0]:
                if "ГРУППА" in cell:
                    group_count += 1

            for group_num in range(group_count):
                group_tables.append(
                    [[line[0][:5] + "-" + line[0][-5:], ] + line[1 + group_num * 2:3 + group_num * 2]
                     for line in table])

        for table in group_tables:
            # Удаление пробелов в названии группы
            table[0][1] = table[0][1].replace(' ', "")
            for line in reversed(table):
                if not line[1]:
                    table.remove(line)
                else:
                    break

        return group_tables

    def get_tables(self):
        return self.__tables_to_group_tables(
            self.__text_tables_to_tables(
                self.__pars_today_tables()))

    def __pars_spans_text(self):
        spans = self.soup.find_all("b")
        spans_text = [span.text for span in spans if "(" in span.text]
        return spans_text

    def __theme_0(self, table, column_width):
        table_str = ""
        for line_num, line in enumerate(table):
            for cell_num, cell in enumerate(line):

                if not (line_num == 0 and cell_num == 0):
                    if line_num == 0 and cell_num == 1:
                        table_str += cell.title().ljust((column_width[cell_num] + column_width[cell_num - 1] + 3), " ")
                    else:
                        table_str += cell.title().ljust(column_width[cell_num], " ")

                    if not cell == line[-1]:
                        table_str += " | "

            table_str += "\n"
        return table_str

    def __theme_1(self, table, column_width):
        table_str = ""
        for line_num, line in enumerate(table):
            for cell_num, cell in enumerate(line):

                if not (line_num == 0 and cell_num == 0):
                    if cell_num == 0:
                        table_str += str(line_num)

                    elif line_num == 0 and cell_num == 1:
                        table_str += cell.title().ljust((column_width[cell_num] + 4), " ")

                    else:
                        table_str += cell.title().ljust(column_width[cell_num], " ")

                    if not cell == line[-1]:
                        table_str += " | "

            table_str += "\n"
        return table_str

    def table_to_str(self, table, style_id: int):
        column_width = []
        for column in range(len(table[0])):
            max_width = 0
            for line in table[1:]:
                width = len(line[column])
                if width > max_width:
                    max_width = width
            column_width.append(max_width)

        if style_id == 0:
            table_str = self.__theme_0(table, column_width)
        elif style_id == 1:
            table_str = self.__theme_1(table, column_width)
        else:
            table_str = self.__theme_0(table, column_width)

        date = self.get_today_date()
        table_str = date + "\n" + table_str

        table_str = table_str.replace("Группа", " Группа")

        if table_str.count("\n") <= 2:
            table_str = table_str.split("Группа")[0]
            table_str += "Группа\nПар нет\n"

        return table_str


if __name__ == '__main__':
    pars = Parser("http://www.katt44.ru/index.php?option=com_content&view=article&id=252&Itemid=129")
    for i in pars.get_tables():
        print(pars.table_to_str(i, style_id=0))
