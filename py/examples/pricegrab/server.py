import glyph

import model


m = glyph.Router()

@m.default()
class PriceService(glyph.r):
    def flight(from_, to_, passengers, date):
        return model.get_flight_price(from_, to_, passengers, date)


if __name__ == '__main__':
    s = glyph.Server(m)
    s.start()
    print s.url
    try:
        s.join()
    finally:
        s.stop()

