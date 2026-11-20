from .orders import OrdersApiEndpoints
from .requests import RequestsApiEndpoints


def setup(api):
    RequestsApiEndpoints(api)
    # After the fixed request paths, so `requests/{request_id}/` does not shadow them
    OrdersApiEndpoints(api)
