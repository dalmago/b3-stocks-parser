import getpass
import os

import requests
from bs4 import BeautifulSoup, element

from stock_data import StockData


class B3StockParser:
    __B3_HOME_URL = "https://cei.b3.com.br/CEI_Responsivo/login.aspx"
    __B3_TRANSACTIONS_URL = "https://cei.b3.com.br/CEI_Responsivo/negociacao-de-ativos.aspx"
    __STOCKS_TABLE_ID = "ctl00_ContentPlaceHolder1_rptAgenteBolsa_ctl00_rptContaBolsa_ctl00_pnResumoNegocios"

    def __init__(self, user: str = None, passwd: str = None) -> None:
        self.user = user
        self.passwd = passwd
        # self.progress = 0
        # self.error = False

        # Variables used to carry data between the requests. Are basically tokens and cookies.
        self._view_state = ""
        self._event_validation = ""
        self._view_state_generator = ""
        self._investor = ""
        self._date_from = ""
        self._date_to = ""
        self._institution = ""
        self._stocks_table = []

        self.__result = None
        # self.__parse_over = Event()

    def parse(self) -> list:
        if self.user is None or self.passwd is None:
            raise RuntimeError("Must set user and password before start parsing.")

        self.__result = None
        print("Connecting")

        if not self.__get_login_page():
            raise RuntimeError("Unable to get login page")

        print("Accessing B3 CEI page")

        if not self.__login():
            raise RuntimeError("Unable to login. Check user name and password.")

        print("Loged in")

        if not self.__get_transactions_page():
            raise RuntimeError("Unable to get transactions page.")

        print("Reading transactions")

        if not self.__get_transactions():
            raise RuntimeError("Unable to get list of transactions.")

        # Must be called twice, for some reason. The first time returns just the same page again, with different
        # view state and event validation, but without the result table. This behavior happens even when accessing
        # through the browser.
        if not self.__get_transactions():
            raise RuntimeError("Unable to get list of transactions.")

        print("Parsing table")

        if not self.__find_stocks():
            raise RuntimeError("Unable to parse stocks table.")

        print("Done")
        return self._stocks_table.copy()

    def __get_login_page(self) -> bool:
        res = requests.get(B3StockParser.__B3_HOME_URL)
        if res.status_code != 200:
            return False

        return self.__find_html_attributes(res.text)

    def __login(self) -> bool:
        res = requests.post(B3StockParser.__B3_HOME_URL, data={  # Login
            "ctl00$ContentPlaceHolder1$txtLogin": self.user,
            "ctl00$ContentPlaceHolder1$txtSenha": self.passwd,
            "ctl00$ContentPlaceHolder1$btnLogar": "Entrar",
            "__VIEWSTATE": self._view_state,
            "__EVENTVALIDATION": self._event_validation,
            "__VIEWSTATEGENERATOR": self._view_state_generator
        })

        if res.status_code != 200:
            return False

        self._investor = res.cookies.get("Investidor", None)
        return self._investor is not None

    def __get_transactions_page(self) -> bool:
        res = requests.get(B3StockParser.__B3_TRANSACTIONS_URL, cookies={
            "Investidor": self._investor
        })
        if res.status_code != 200:
            return False

        return self.__find_html_attributes(res.text, True)

    def __get_transactions(self) -> bool:
        res = requests.post(B3StockParser.__B3_TRANSACTIONS_URL, cookies={
            "Investidor": self._investor
        }, data={
            "ctl00$ContentPlaceHolder1$ddlAgentes": self._institution,
            "ctl00$ContentPlaceHolder1$ddlContas": "0",  # self._account,
            "ctl00$ContentPlaceHolder1$txtDataDeBolsa": self._date_from,
            "ctl00$ContentPlaceHolder1$txtDataAteBolsa": self._date_to,
            "ctl00$ContentPlaceHolder1$btnConsultar": "Consultar",
            "__VIEWSTATE": self._view_state,
            "__EVENTVALIDATION": self._event_validation,
            "__VIEWSTATEGENERATOR": self._view_state_generator
        })

        if res.status_code != 200:
            return False

        if self.__find_html_attributes(res.text, True):
            self.__result = res.text
            return True
        return False

    def __find_html_attributes(self, html_data: str, read_form_fields: bool = False) -> bool:
        soup = BeautifulSoup(html_data, 'html.parser')

        view_state = soup.find('input', id="__VIEWSTATE")
        if view_state is None:
            return False
        self._view_state = view_state.get('value', '')

        event_validation = soup.find('input', id="__EVENTVALIDATION")
        if event_validation is None:
            return False
        self._event_validation = event_validation.get('value', '')

        view_state_gen = soup.find('input', id="__VIEWSTATEGENERATOR")
        if view_state_gen is None:
            return False
        self._view_state_generator = view_state_gen.get('value', '')

        if read_form_fields:
            date_from = soup.find('input', id="ctl00_ContentPlaceHolder1_txtDataDeBolsa")
            if date_from is None:
                return False
            self._date_from = date_from.get('value', '')

            date_to = soup.find('input', id="ctl00_ContentPlaceHolder1_txtDataAteBolsa")
            if date_to is None:
                return False
            self._date_to = date_to.get('value', '')

            inst_sel = soup.find('select', id="ctl00_ContentPlaceHolder1_ddlAgentes")
            if inst_sel is None:
                return False
            for inst in inst_sel.children:
                if type(inst) is element.Tag:
                    if inst.get('selected', '') == 'selected':
                        self._institution = inst.get('value', '')
                        return True
        return True

    def __find_stocks(self) -> bool:
        if self.__result is None:
            return False

        soup = BeautifulSoup(self.__result, 'html.parser')
        stocks_table = soup.find('div', id=B3StockParser.__STOCKS_TABLE_ID)
        if stocks_table is None:
            return False

        try:
            rows = stocks_table.table.tbody.find_all('tr')
            for row in rows:
                self._stocks_table.append(StockData(row))

        except AttributeError:
            return False

        return True

    # def get_progress(self) -> int:
    #     return self.progress

    def set_auth(self, user: str, passwd: str) -> None:
        self.user = user
        self.passwd = passwd


if __name__ == "__main__":
    if 'B3_USER' in os.environ.keys() and 'B3_PASSWD' in os.environ.keys():
        b3user = os.getenv('B3_USER')
        b3passwd = os.getenv('B3_PASSWD')
    else:
        b3user = input("B3 user:")
        b3passwd = getpass.getpass("B3 password:")

    cei = B3StockParser(b3user, b3passwd)
    mystocks = cei.parse()

    for stock in mystocks:
        print(stock)
