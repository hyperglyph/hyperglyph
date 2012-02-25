import hate
import datetime


def client(url):
price_server = hate.get(url)

print price_server.flight('a','b',1, datetime.datetime.now()
