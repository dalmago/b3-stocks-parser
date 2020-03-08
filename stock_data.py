import csv
from typing import ClassVar, Dict
from datetime import date, datetime

from bs4 import element

TAXES_FILE = 'taxas_corretoras.csv'


class StockData:

    __taxes_dict: ClassVar[Dict] = None

    def __init__(self, table_row: element, agent: str = "") -> None:
        self.code: str = ""
        self.buy_date: date = None
        self.sell_date: date = None
        self.buy_price: float = 0
        self.sell_price: float = 0
        self.buy_amount: int = 0
        self.sell_amount: int = 0
        self.position: str = None
        self.agent: str = agent

        if StockData.__taxes_dict is None:
            StockData.__taxes_dict = self.__parse_tax_file()

        self.__initialized = False

        if table_row is not None:
            self.__parse_row(table_row)

    def __parse_row(self, row: element) -> None:
        data_list = row.find_all('td')
        self.code = data_list[0].text.strip()

        period = data_list[1].span.text.strip()
        if ' a ' in period:
            buy, sell = period.split(' a ')
        else:
            buy = period
            sell = None

        self.buy_date = datetime.strptime(buy, "%d/%m/%Y").date()
        if sell is not None:
            self.sell_date = datetime.strptime(sell, "%d/%m/%Y").date()
        else:
            self.sell_date = None

        self.buy_amount = int(data_list[2].text.strip())
        self.sell_amount = int(data_list[3].text.strip())
        self.buy_price = float(data_list[4].text.strip().replace(',', '.'))
        self.sell_price = float(data_list[5].text.strip().replace(',', '.'))

        self.position = data_list[7].text.strip()
        self.__initialized = True

    def __parse_tax_file(self):
        tax_dict = {}
        try:
            with open(TAXES_FILE, 'r') as csv_file:
                csv_dict = csv.DictReader(csv_file)
                for agent_tax in csv_dict:
                    tax_dict[agent_tax['cod']] = {
                        "corr": agent_tax['corretagem'],
                        "iss": agent_tax['ISS'],
                        "liquid": agent_tax['liquidacao'],
                        "emol": agent_tax['emolumentos'],
                        "name": agent_tax['nome']
                    }
        except FileNotFoundError:
            pass

        return tax_dict

    def __str__(self) -> str:
        if self.__initialized:
            if self.position == 'ZERADA':
                return (f"{self.code}: {self.buy_amount} stocks, profit: "
                        f"R${self.sell_amount * (self.sell_price - self.buy_price):.2f}")
            elif self.position == 'COMPRADA':
                return f"{self.code}: {self.buy_amount} stocks, bought at: {self.buy_date}, R${self.buy_price}"
            else:
                return "Position type not implemented yet"
        else:
            return "Stock not initialized"
