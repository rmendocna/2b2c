from datetime import datetime
import re
import sys
import uuid
from time import sleep, time
from threading import Thread

import requests

QUANTITY_RE = re.compile(r"^\d+(\.\d+)?$")
IS_LIVE = True
stop_thread = False


api_token = 'e13e627c49705f83cbe7b60389ac411b6f86fee7'
headers = {'Authorization': 'Token %s' % api_token}
api_host = "https://api.uat.b2c2.net/"

api_errors = {
    1000: 'Generic –- Unknown error.',
    1001: 'Instrument not allowed – Instrument does not exist or you are not authorized to trade it.',
    1002: 'The RFQ does not belong to you.',
    1003: 'Different instrument – You tried to post a trade with a different instrument than the related RFQ.',
    1004: 'Different side – You tried to post a trade with a different side than the related RFQ.',
    1005: 'Different price – You tried to post a trade with a different price than the related RFQ.',
    1006: 'Different quantity – You tried to post a trade with a different quantity than the related RFQ.',
    1007: 'Quote is not valid – Quote may have expired.',
    1009: 'Price not valid – The price is not valid anymore. This error can occur during big market moves.',
    1010: 'Quantity too big – Max quantity per trade reached.',
    1011: 'Not enough balance – Not enough balance.',
    1012: 'Max risk exposure reached – Please see our FAQ for more information about the risk exposure.',
    1013: 'Max credit exposure reached – Please see our FAQ for more information about the credit exposure.',
    1014: 'No BTC address associated – You don’t have a BTC address associated to your account.',
    1015: 'Too many decimals – We only allow four decimals in quantities.',
    1016: 'Trading is disabled – May occur after a maintenance or under exceptional circumstances.',
    1017: 'Illegal parameter – Wrong type or parameter.',
    1018: 'Settlement is disabled at the moment.',
    1019: 'Quantity is too small.',
    1020: 'The field valid_until is malformed.',
    1021: 'Your Order has expired.',
    1022: 'Currency not allowed.',
    1023: 'We only support “FOK” order_type at the moment.',
    1101: 'Field required – Field required.',
    1102: 'Pagination offset too big – Narrow down the data space using parameters such as ‘created_gte’, ‘created_lt’, ‘since’.',
    1200: 'API Maintenance',
    1500: 'This contract is already closed.',
    1501: 'The given quantity must be smaller or equal to the contract quantity.',
    1502: 'You don’t have enough margin. Please add funds to your account or close some positions.',
    1503: 'Contract updates are only for closing a contract.',
    1100: 'Other error.',
}

STOCK_INSTRUMENTS = [
    {"name": "BTCUSD.CFD"},
    {"name": "BTCUSD.SPOT"},
    {"name": "BTCEUR.SPOT"},
    {"name": "BTCGBP.SPOT"},
    {"name": "ETHBTC.SPOT"},
    {"name": "ETHUSD.SPOT"},
    {"name": "LTCUSD.SPOT"},
    {"name": "XRPUSD.SPOT"},
    {"name": "BCHUSD.SPOT"}
 ]


def hold():
    input('Press any key to continue')


def get_instruments():
    if IS_LIVE:
        try:
            resp = requests.get("%sinstruments/" % api_host, headers=headers)
        except Exception as e:
            return e
        else:
            data = resp.json()
            return data
    else:
        return STOCK_INSTRUMENTS


def _print_options(lst, last="BACK"):
    for ite, item in enumerate(lst):
        x = ite + 1
        print(f"{x}: {item}")
    print(f"0: {last}")


def _get_choice(ln, question):
    choice = None
    while choice is None:
        user_input = input(question)
        try:
            choice = int(user_input)
        except:
            pass
        else:
            if choice < 0 or choice > ln:
                choice = None
            else:
                break
        print('Please choose one of the available options')
    return choice


def choose_instrument():
    instruments = [x["name"] for x in get_instruments()]
    _print_options(instruments, "QUIT")
    choice = _get_choice(len(instruments), "Choose instrument (N.): ")
    if choice == 0:
        sys.exit(0)
    else:
        instr = instruments[choice - 1]
        return instr


def choose_side():
    sides = ['BUY', 'SELL']
    _print_options(sides)
    choice = _get_choice(len(sides), "Buy or Sell (choose N.): ")
    if choice == 0:
        start()
    else:
        side = sides[choice - 1]
        return side.lower()


def enter_quantity():
    choice = None
    while choice is None:
        user_input = input("Quantity: (0 to cancel): ")
        if QUANTITY_RE.match(user_input):
            if choice == "0":
                start()
            else:
                choice = user_input
                break
        print("Please enter a quantity")
    return choice


def rfq(instrument, side, quantity):
    uid = str(uuid.uuid4())
    payload = {
        'instrument': instrument,
        'side': side,
        'quantity': str(quantity),
        'client_rfq_id': uid
    }
    try:
        resp = requests.post("%srequest_for_quote/" % api_host, json=payload, headers=headers)
    except Exception as e:
        return e
    else:
        data = resp.json()
        if resp.status_code >= 400:
            for e in data['errors']:
                if e['field'] == 'non_field_errors':
                    print("%(code)s: %(message)s" % e)
                else:
                    print("%(code)s: [%(field)s] %(message)s" % e)
            return None
        else:
            return data


def order(quote):
    # exceptions handled upstream
    payload = quote.copy()
    for attr in ["rfq_id", "client_rfq_id", "created"]:
        del payload[attr]

    valid_until = datetime.utcfromtimestamp(time() + 10).strftime("%Y-%m-%dT%H:%M:%S")
    uid = str(uuid.uuid4())
    executing_unit = 'risk-adding-strategy'

    payload.update({
        'client_order_id': uid,
        'order_type': 'FOK',
        'valid_until': valid_until,
        'executing_unit': executing_unit,
    })

    resp = requests.post("%sorder/" % api_host, json=payload, headers=headers)
    if resp.status_code < 300:
        return resp.json()
    else:
        raise ValueError(resp.status_code)


def print_quote(quote):
    price = quote['price']
    currency = quote['instrument'][3:6]
    print(f"PRICE: {currency} {price}")


def countdown(ts):
    for i in reversed(range(15)):
        global stop_thread
        if datetime.now() > ts or stop_thread:
            break
        print(i, end='\r')
        sleep(1)
    return


def start_counter(limit):

    """Attempt to print a fancy countdown"""

    th = Thread(target=countdown, args=(limit,))
    th.daemon = True
    th.start()
    return th


def check_purchase(purchase, quote):
    # for attr in ('client_order_id', 'executing_unit'):
    #   assert purchase[attr] == quote[attr]
    # many checks could be made
    return True


def print_balance():
    resp = requests.get(f"{api_host}balance/", headers=headers)
    balance = resp.json()
    print('')
    print('Your balance:')
    for k, v in balance.items():
        print(f"{k}: {v}")


def start():
    global stop_thread
    while True:
        instr = choose_instrument()
        print(instr)
        sid = choose_side()
        print(f"{instr} | {sid}")
        quant = enter_quantity()

        quote = rfq(instr, sid, quant)
        if not quote:
            hold()
            continue
        print_quote(quote)

        tstamp = quote['valid_until']
        if tstamp[-1] == 'Z':
            tstamp = tstamp[:-1]
        limit = datetime.fromisoformat(tstamp)

        th = start_counter(limit)

        proceed = ''
        while proceed.upper() not in ['Y', 'N', 'YES', 'NO']:
            if len(proceed):
                print('Please choose (Y)es or (N)o', end='\r')
            proceed = input('Do you want to proceed? (Yes/No)')
        proceed = proceed.upper()
        if proceed[0] == 'Y':
            if th.is_alive():
                stop_thread = True
                try:
                    purchase = order(quote)
                except Exception as e:
                    print("%s" % e)
                else:
                    try:
                        check_purchase(purchase, quote)
                    except Exception as e:
                        print('Invalid order/ purchase data')
                    else:
                        print_balance()
            else:
                print('TIMED OUT')
        hold()


if __name__ == '__main__':
    start()
