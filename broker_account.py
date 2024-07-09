import redis
import json
import upstox_client
from upstox_client.rest import ApiException

class BrokerAccount(object):
    def __init__(self, access_token = None, api_version= "v2"):
        if access_token is None:
            raise("Access token is not provided or is none")
        else:
            self.access_token = access_token
            self.api_version = api_version
            self.use_redis = True
            self.redis_connection = redis.Redis(host='localhost', port=6379)
            self.order_book = None
            self.positions = None
            self.holdings = None
    
    def print_output(self, message):
        tz = timezone('Asia/Kolkata')
        print(f">>>> {datetime.datetime.now(tz)} >>>> {message}")

    def write_to_redis(self, key, value):
        try:
            self.redis_connection.set(key, json.dumps(value))
        except redis.RedisError as e:
            print(f"Redis error: {e}")

    def read_from_redis(self, key):
        try:
            retrieved_data = json.loads(self.redis_connection.get(key))
            return retrieved_data
        except redis.RedisError as e:
            print(f"Redis error: {e}")
            return None

    def get_positions_from_broker(self):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.PortfolioApi(upstox_client.ApiClient(configuration))
        try:
            api_response = api_instance.get_positions(self.api_version)
            positions = api_response.data
            self.positions = positions
            return positions
        except ApiException as e:
            print("Exception when calling PortfolioApi->get_positions: %s\n" % e)
            return None

    def get_orderbook_from_broker(self):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
        try:
            # Get order book
            api_response = api_instance.get_order_book(self.api_version)
            order_book = api_response.data
            self.order_book = order_book
            return order_book
        except ApiException as e:
            print("Exception when calling OrderApi->get_order_book: %s\n" % e)

    def fetch_order_details(self, order_id):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
        try:
            # Get order details
            api_response = api_instance.get_order_details(self.api_version, order_id=order_id)
            order_detail = api_response.data
            return order_detail
        except ApiException as e:
            print("Exception when calling OrderApi->get_order_details: %s\n" % e)

    def cancel_order(self, order_id):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        try:
            api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
            api_response = api_instance.cancel_order(order_id, self.api_version)
            print(f">>>> Cancelling Order {order_id} is {api_response.status}")
        except ApiException as e:
            print("Exception when calling OrderApi->cancel_order: %s\n" % e)

    def place_entry_order(self, instrument_key, quantity, price, trigger_price):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
        body = upstox_client.PlaceOrderRequest(
            quantity= quantity,
            product="I",
            validity="DAY",
            instrument_token= instrument_key,
            price= price,
            tag= f"ENTRY-ORDER-{instrument_key}",
            order_type="SL",
            transaction_type= "SELL",
            disclosed_quantity= 0,
            trigger_price=trigger_price,
            is_amo=False
        )

        try:
            api_response = api_instance.place_order(body, self.api_version)
            order_id = api_response.data.order_id
            return order_id
        except ApiException as e:
            print("Exception when calling OrderApi->place_order: %s\n" % e)

    def place_stop_loss_order(self, instrument_key, quantity, price, trigger_price):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
        body = upstox_client.PlaceOrderRequest(
            quantity= quantity,
            product="I",
            validity="DAY",
            instrument_token= instrument_key,
            price= price,
            tag= f"STOP-LOSS-ORDER-{instrument_key}",
            order_type="SL",
            transaction_type= "BUY",
            disclosed_quantity= 0,
            trigger_price=trigger_price,
            is_amo=False
        )

        try:
            api_response = api_instance.place_order(body, self.api_version)
            order_id = api_response.data.order_id
            return order_id
        except ApiException as e:
            print("Exception when calling OrderApi->place_order: %s\n" % e)

    def place_market_exit_order(self, instrument_key, quantity):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
        body = upstox_client.PlaceOrderRequest(
            quantity= quantity,
            product="I",
            validity="DAY",
            instrument_token= instrument_key,
            price= 0,
            tag= f"EXIT-ORDER-{instrument_key}",
            order_type="MARKET",
            transaction_type= "BUY",
            disclosed_quantity= 0,
            trigger_price=0,
            is_amo=False
        )

        try:
            api_response = api_instance.place_order(body, self.api_version)
            order_id = api_response.data.order_id
            return order_id
        except ApiException as e:
            print("Exception when calling OrderApi->place_order: %s\n" % e)