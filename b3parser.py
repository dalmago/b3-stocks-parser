import os

from html.parser import HTMLParser

import requests


class B3Parser:
    __B3_HOME_URL = "https://cei.b3.com.br/CEI_Responsivo/login.aspx"
    __B3_TRANSACTIONS_URL = "https://cei.b3.com.br/CEI_Responsivo/negociacao-de-ativos.aspx"

    def __init__(self, user: str = None, passwd: str = None) -> None:
        self.user = user
        self.passwd = passwd
        # self.progress = 0
        # self.error = False
        self.result = None

        # Variables used to carry data between the requests. Are basically tokens and cookies.
        self._view_state = ""
        self._event_validation = ""
        self._view_state_generator = ""
        self._investor = ""
        self._date_from = ""
        self._date_to = ""
        self._institution = ""

        self.__view_state_found = False
        self.__event_validation_found = False
        self.__view_state_gen_found = False
        self.__date_to_found = False
        self.__date_from_found = False
        self.__institution_found = False
        self.__entering_inst_select = False

        self.__read_form_fields = False
        self.__html_parser = HTMLParser()
        self.__html_parser.handle_starttag = self.__find_html_attributes

        # self.__parse_over = Event()

    def parse(self) -> None:
        if self.user is None or self.passwd is None:
            raise RuntimeError("Must set user and password before start parsing.")

        if not self.__get_login_page():
            raise RuntimeError("Unable to get login page")

        print("Accessing B3 CEI page")

        if not self.__login():
            raise RuntimeError("Unable to login. Check user name and password.")

        print("Loged in")

        self.__read_form_fields = True  # Enable reading extra fields from form
        if not self.__get_transactions_page():
            raise RuntimeError("Unable to get transactions page.")

        print("Reading transactions")

        if not self.__get_transactions():
            raise RuntimeError("Unable to get list of transactions.")

        # Must be called twice, for some reason. The first time returns just the same page again, with different
        # view state and event validation.
        if not self.__get_transactions():
            raise RuntimeError("Unable to get list of transactions.")

        with open('output.html', 'w') as f:
            f.write(self.result)
        print("Done")

    def __get_login_page(self) -> bool:
        res = requests.get(B3Parser.__B3_HOME_URL)
        if res.status_code != 200:
            return False

        self.__clear_temp_params()
        self.__html_parser.feed(res.text)  # Find HTML attributes

        return self.__view_state_found and self.__event_validation_found and self.__view_state_gen_found

    def __login(self) -> bool:
        res = requests.post(B3Parser.__B3_HOME_URL, data={  # Login
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
        res = requests.get(B3Parser.__B3_TRANSACTIONS_URL, cookies={
            "Investidor": self._investor
        })
        if res.status_code != 200:
            return False

        self.__clear_temp_params()
        self.__html_parser.feed(res.text)  # Find HTML attributes

        return (self.__view_state_found and self.__event_validation_found and self.__view_state_gen_found and
                self.__date_from_found and self.__date_to_found and self.__institution_found)

    def __get_transactions(self) -> bool:
        res = requests.post(B3Parser.__B3_TRANSACTIONS_URL, cookies={
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

        self.__clear_temp_params()
        self.__html_parser.feed(res.text)  # Find HTML attributes

        if (self.__view_state_found and self.__event_validation_found and self.__view_state_gen_found and
                self.__date_from_found and self.__date_to_found and self.__institution_found):
            self.result = res.text

            return True
        return False

    def __find_html_attributes(self, tag: str, attr: list) -> None:
        if self.__view_state_found and self.__event_validation_found and self.__view_state_gen_found:
            if not self.__read_form_fields or (self.__date_from_found and self.__date_to_found and
                                               self.__institution_found):

                # self.__html_parser.reset()  # All elements found
                return

        # if tag == 'form' or self.__form_data:
        # Inside form tag
        # self.__form_data = True
        if tag == 'input':
            attr_dict = dict(attr)
            if attr_dict.get('name', '') == "__VIEWSTATE":
                self._view_state = attr_dict.get('value', '')
                self.__view_state_found = True

            elif attr_dict.get('name', '') == "__EVENTVALIDATION":
                self._event_validation = attr_dict.get('value', '')
                self.__event_validation_found = True

            elif attr_dict.get('name', '') == "__VIEWSTATEGENERATOR":
                self._view_state_generator = attr_dict.get('value', '')
                self.__view_state_gen_found = True
                
            elif attr_dict.get('name', '') == "ctl00$ContentPlaceHolder1$txtDataDeBolsa":
                self._date_from = attr_dict.get('value', '')
                self.__date_from_found = True

            elif attr_dict.get('name', '') == "ctl00$ContentPlaceHolder1$txtDataAteBolsa":
                self._date_to = attr_dict.get('value', '')
                self.__date_to_found = True

        elif self.__read_form_fields and tag == 'select':
            attr_dict = dict(attr)
            if attr_dict.get('name', '') == "ctl00$ContentPlaceHolder1$ddlAgentes":
                self.__entering_inst_select = True

            # elif attr_dict.get('name', '') == "ctl00$ContentPlaceHolder1$ddlContas":
            #     self._account = attr_dict.get('value', '')
            #     self.__account_found = True

        elif self.__read_form_fields and self.__entering_inst_select and tag == 'option':
            attr_dict = dict(attr)
            if 'selected' in attr_dict.keys():
                self._institution = attr_dict.get('value', '')
                self.__institution_found = True
                self.__entering_inst_select = False

    def __clear_temp_params(self) -> None:
        self._view_state = ""
        self._event_validation = ""
        self._view_state_generator = ""
        self._date_from = ""
        self._date_to = ""
        self._institution = ""

        self.__view_state_found = False
        self.__event_validation_found = False
        self.__view_state_gen_found = False
        self.__date_from_found = False
        self.__date_to_found = False
        self.__institution_found = False
        self.__entering_inst_select = False

        # self.__form_data = False
        self.__html_parser.reset()

    # def get_progress(self) -> int:
    #     return self.progress

    def set_auth(self, user: str, passwd: str) -> None:
        self.user = user
        self.passwd = passwd


if __name__ == "__main__":
    cei = B3Parser(os.getenv('B3_USER'), os.getenv('B3_PASSWD'))
    cei.parse()
