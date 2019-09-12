import getpass
import os
import logging
import json
from typing import Dict

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from b3parser import B3StockParser

BASE_URL = "https://br.tradingview.com/symbols/BMFBOVESPA-%s/"
LOCAL_FILE = "b3parser/stocks.json"

options = Options()
options.headless = True


def read_local() -> Dict:
    if os.path.exists(LOCAL_FILE):
        try:
            with open(LOCAL_FILE, 'r') as f:
                return json.load(f)

        except Exception as e:
            logging.error("Error loading local file: %s" % e)

    logging.info("Generating new local file")
    with open(LOCAL_FILE, 'w') as f:
        json.dump({}, f)

    return {}


def write_local(configs: Dict) -> None:
    with open(LOCAL_FILE, 'w') as f:
        json.dump(configs, f)


def get_current_price(stock_code: str, sel_driver: webdriver.Firefox) -> float:
    logging.debug("Getting current price for %s" % stock_code)

    sel_driver.get(BASE_URL % stock_code)
    logging.debug("URL loaded")
    value_text = ""

    try:
        data_div = sel_driver.find_element_by_id("js-category-content")
        value_div = data_div.find_element_by_class_name("js-symbol-last")
        value_text = value_div.text
        value = float(value_text)
        logging.debug("Got value %s" % value)

        return value
    except Exception as e:
        logging.error("Error getting value: %s" % e)
        logging.error("value_text: %s" % value_text)

    return 0


if __name__ == "__main__":
    logging.basicConfig(filename='b3parser/quotes.log', format='%(levelname)s:%(asctime)s:%(message)s',
                        level=logging.DEBUG)
    logging.debug("Starting")
    driver = webdriver.Firefox(options=options)

    if 'B3_USER' in os.environ.keys() and 'B3_PASSWD' in os.environ.keys():
        b3user = os.getenv('B3_USER')
        b3passwd = os.getenv('B3_PASSWD')
    else:
        b3user = input("B3 user CPF: ")
        b3user.replace('.', '')
        b3user.replace('-', '')
        b3passwd = getpass.getpass("B3 password: ")

    local_info = read_local()
    price_diff = {}

    cei = B3StockParser(b3user, b3passwd)
    all_stocks = cei.parse()
    my_stocks = filter(lambda s: s.position == 'COMPRADA', all_stocks)

    for stock in my_stocks:

        current_price = get_current_price(stock.code, driver)
        if current_price == 0:
            continue

        if stock.code in local_info.keys():
            price_diff[stock.code] = current_price - local_info[stock.code]

        local_info[stock.code] = current_price

    logging.info("Result diff: %s" % price_diff)
    write_local(local_info)
