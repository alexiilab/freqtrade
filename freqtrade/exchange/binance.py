import logging
import requests
from typing import Dict, List, Optional
import datetime

# from bittrex.bittrex import Bittrex as _Bittrex
# from bittrex.bittrex import API_V1_1, API_V2_0
# from requests.exceptions import ContentDecodingError

from binance.client import Client as _Binance


from freqtrade import OperationalException
from freqtrade.exchange.interface import Exchange

logger = logging.getLogger(__name__)

# _API: _Bittrex = None
# _API_V2: _Bittrex = None
_EXCHANGE_CONF: dict = {}

# API socket timeout
API_TIMEOUT = 60


def custom_requests(request_url, apisign):
    """
    Set timeout for requests
    """
    return requests.get(
        request_url,
        headers={"apisign": apisign},
        timeout=API_TIMEOUT
    ).json()


class Binance(Exchange):
    """
    Binance exchange.
    """
    # Base URL and API endpoints
    BASE_URL: str = 'https://www.binance.com'
    # PAIR_DETAIL_METHOD: str = BASE_URL + '/Market/Index'

    def __init__(self, config: dict) -> None:
        # global _API, _API_V2, _EXCHANGE_CONF

        # _EXCHANGE_CONF.update(config)
        # _API = _Bittrex(
        #     api_key=_EXCHANGE_CONF['key'],
        #     api_secret=_EXCHANGE_CONF['secret'],
        #     calls_per_second=1,
        #     api_version=API_V1_1,
        #     dispatch=custom_requests
        # )
        # _API_V2 = _Bittrex(
        #     api_key=_EXCHANGE_CONF['key'],
        #     api_secret=_EXCHANGE_CONF['secret'],
        #     calls_per_second=1,
        #     api_version=API_V2_0,
        #     dispatch=custom_requests
        # )
        
        global	_API, _EXCHANGE_CONF
        _EXCHANGE_CONF.update(config)
        _API = _Binance(api_key, api_secret)


        self.cached_ticker = {}
        #init pair name conversion hashes
        # freqtrade use XXX_YYY and binance use XXXYYY
        self.ft2bin_pair_name = {}
        self.bin2ft_pair_name = {}
        for s in _API.exchange_info()['symbols']:
            self.ft2bin_pair_name[s['symbol']] = "{}_{}".format(s['baseAsset'], s['quoteAsset'])
            self.bin2ft_pair_name["{}_{}".format(s['baseAsset'], s['quoteAsset'])] = [s['symbol']]


    @staticmethod
    def _validate_response(response) -> None:
        """
        Validates the given bittrex response
        and raises a ContentDecodingError if a non-fatal issue happened.
        """
        # temp_error_messages = [
        #     'NO_API_RESPONSE',
        #     'MIN_TRADE_REQUIREMENT_NOT_MET',
        # ]
        # if response['message'] in temp_error_messages:
        #     raise ContentDecodingError('Got {}'.format(response['message']))
        return


    @property
    def fee(self) -> float:
        # 0.05 %: See https://www.binance.com/fees.html
        return 0.0005
#done
    def buy(self, pair: str, rate: float, amount: float) -> str:
        data = _API.order_limit_buy(symbol=self.ft2bin_pair_name(pair), quantity=amount, price=rate )
        return data['clientOrderId']
#done
    def sell(self, pair: str, rate: float, amount: float) -> str:
        data = _API.order_limit_sell(symbol=self.ft2bin_pair_name(pair), quantity=amount, price=rate)

#done
    def get_balance(self, currency: str) -> float:
        data = _API.get_asset_balance(asset=currency)
        return float(data['free'])

#done
    def get_balances(self):
        data = _API.get_account()
        r = []
        for b in data['balances']:
        	r. append({'Available': b['free'],
        			   'Pending' : b['locked'],
        			   'Balance' :  Available + Pending,
        			   'Currency': b['asset']})
        return r


    def get_ticker(self, pair: str, refresh: Optional[bool] = True) -> dict:
        if refresh or pair not in self.cached_ticker.keys():
            data = _API.get_ticker(symbol=self.ft2bin_pair_name(pair))
            self.cached_ticker[pair] = {
                'bid': float(data['bidPrice']),
                'ask': float(data['askPrice']),
                'last': float(data['lastPrice']),
            }
        return self.cached_ticker[pair]

    def get_ticker_history(self, pair: str, tick_interval: int) -> List[Dict]:
        if tick_interval == 1:
            interval = '1m'
        elif tick_interval == 5:
            interval = '5m'
        elif tick_interval == 30:
            interval = '30m'
        elif tick_interval == 60:
            interval = '1h'
        elif tick_interval == 1440:
            interval = '1d'
        else:
            raise ValueError('Cannot parse tick_interval: {}'.format(tick_interval))

        klines = _API.get_klines(symbol = self.ft2bin_pair_name(pair) , interval = interval)
        r = []
        for kl in klines:
        	r.append({
        		'O': kl[1],
        		'H': kl[2],
        		'L': kl[3],
        		'C': kl[4],
        		'V': kl[5],
        		'T': datetime.datetime.fromtimestamp(kl[0]//1000.0),
        		'BV': kl[7]
        		})


        return r

##todo here
    def get_order(self, order_id: str) -> Dict:
        #    :return: dict, format: {
        #     'id': str,
        #     'type': str,
        #     'pair': str,
        #     'opened': str ISO 8601 datetime,
        #     'closed': str ISO 8601 datetime,
        #     'rate': float,
        #     'amount': float,
        #     'remaining': int
        # }
        data = _API.get_order()
        
#todo
    def cancel_order(self, order_id: str) -> None:
        data = _API.cancel(order_id)
        if not data['success']:
            Bittrex._validate_response(data)
            raise OperationalException('{message} params=({order_id})'.format(
                message=data['message'],
                order_id=order_id))

#done
    def get_pair_detail_url(self, pair: str) -> str:
        return self.BASE_URL + 'trade.html?symbol={}'.format(pair)


#done
    def get_markets(self) -> List[str]:
        data = _API.get_exchange_info()
        return [self.bin2ft_pair_name(s['symbol']) for s in data['symbols']]


    def get_market_summaries(self) -> List[Dict]:
        data = _API.get_ticker()
        r = []
        for s in data:
            r.append(
                {
                'MarketName': self.bin2ft_pair_name(s['symbol']),
                'High': s['highPrice'],
                'Low': s['lowPrice'],
                'Volume': s['volume'],
                'Last': s['lastPrice'],
                'TimeStamp': datetime.datetime.fromtimestamp(s[closeTime]//1000.0),,
                'BaseVolume': s['quoteVolume'],
                'Bid': s['bidPrice'],
                'Ask': s['askPrice'],
                'OpenBuyOrders': 0,   # todo
                'OpenSellOrders': 0,  #todo
                'PrevDay': 0,  #todo
                'Created': datetime.datetime(2017,7,1,0,0) #todo
                }
                )
        return r

    def get_wallet_health(self) -> List[Dict]:
#todo : dont fake results
        data = _API.get_exchange_info()
        return[{
            'Currency': s['baseAsset'],
            'IsActive': True,
            'LastChecked': str(datetime.now()),
            'Notice': "",
        } for s in data]


