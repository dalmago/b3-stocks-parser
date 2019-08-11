from datetime import date, datetime

from bs4 import element


class StockData:
    def __init__(self, table_row: element = None) -> None:
        self.code: str = ""
        self.buy_date: date = None
        self.sell_date: date = None
        self.buy_price: float = 0
        self.sell_price: float = 0
        self.buy_amount: int = 0
        self.sell_amount: int = 0
        self.position: str = ""

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

    def __str__(self) -> str:
        if self.__initialized:
            if self.position == 'ZERADA':
                return "%s: %s stocks, profit: R$%.2f" % (self.code, self.buy_amount,
                                                        self.sell_amount * (self.sell_price - self.buy_price))
            elif self.position == 'COMPRADA':
                return "%s: %s stocks, bought at: %s, R$%s" %(self.code, self.buy_amount, self.buy_date, self.buy_price)
            else:
                return "Position type not implemented yet"
        else:
            return "Stock not initialized"
