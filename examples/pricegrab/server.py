import hate

import model


m = hate.Mapper()

@m.default()
class PriceService(hate.r):
    def flight(from_, to_, passengers, date):
        return model.get_flight_price(from_, to_, passengers, date)


if __name__ == '__main__':
    s = hate.Server(m)
    s.start()
    print s.url
    try:
        s.join()
    finally:
        s.stop()

