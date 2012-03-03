import hate
import datetime


def client(url):
    price_server = hate.get(url)

    print price_server.flight('a','b',1, datetime.datetime.now())

if __name__ == '__main__':
    import sys
    client(sys.argv[1])
