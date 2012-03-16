import unittest2
import glyph
import datetime
from pytz import utc



class Test(unittest2.TestCase):
    def testCase(self):
        cases = [
            1,
            1.0,
            "foo",
            u"bar",
            [],
            ['a',1,[2]],
            None,
            True,
            False,
            {'a':1},
            datetime.datetime.utcnow().replace(tzinfo=utc),
        ]
        for c in cases:
            self.assertEqual(c, glyph.parse(glyph.dump(c)))


class NodeTest(unittest2.TestCase):
    def testCase(self):
        cases = [
            glyph.node('doc',attributes=dict(aa=1,b="toot")),
            glyph.form("http://example.org",values=['a','b']),
            glyph.link("http://toot.org")
        ]
        for c in cases:
            self.assertEqual(c, glyph.parse(glyph.dump(c)))



class ServerTest(unittest2.TestCase):
    def setUp(self):
        self.endpoint=glyph.Server(self.router())
        self.endpoint.start()

    def tearDown(self):
        self.endpoint.stop()

class GetTest(ServerTest):
    def setUp(self):
        self.value = 0
        ServerTest.setUp(self)

    def router(self):
        m = glyph.Router()
        @m.default()
        class Test(glyph.r):
            def get(self_):
                return self.value
        return m

    def testCase(self):
        result = glyph.get(self.endpoint.url)

        self.assertEqual(result.get(), self.value)
class NoneTest(ServerTest):

    def router(self):
        m = glyph.Router()
        @m.default()
        class Test(glyph.r):
            def get(self):
                return  None
        return m

    def testCase(self):
        result = glyph.get(self.endpoint.url)

        self.assertEqual(result.get(), None)

class IndexTest(ServerTest):
    def setUp(self):
        ServerTest.setUp(self)

    def router(self):
        m = glyph.Router()
        @m.add()
        class Test(glyph.r):
            def get(self):
                return 1
        @m.add()
        class Other(glyph.r):
            def __init__(self, v=0):
                self.v = v
        return m

    def testCase(self):
        index = glyph.get(self.endpoint.url)

        self.assertEqual(index.Test().get(), 1)
        self.assertEqual(index.Other(4).v,4)
class LinkTest(ServerTest):
    def setUp(self):
        self.value = 0
        ServerTest.setUp(self)

    def router(self):
        m = glyph.Router()
        @m.add()
        class Test(glyph.r):
            def __init__(self, value):
                self.value = int(value)
            def double(self):
                return self.value*2
        @m.default()
        class Root(glyph.r):
            @glyph.redirect()
            def get(self_):
                return Test(self.value)
        return m

    def testCase(self):
        result = glyph.get(self.endpoint.url)
        result = result.get()
        self.assertEqual(result.double(), self.value)


class MethodTest(ServerTest):
    def setUp(self):
        ServerTest.setUp(self)

    def router(self):
        m = glyph.Router()
        @m.default()
        class Test(glyph.r):
            def __init__(self, value=0):
                self.value = int(value)
            @glyph.redirect()
            def inc(self, n):
                return Test(self.value+n)
        return m

    def testCase(self):
        result = glyph.get(self.endpoint.url)
        self.assertEqual(result.value, 0)
        result = result.inc(n=5)

        self.assertEqual(result.value, 5)
        

class LinkEmbedTest(ServerTest):

    def router(self):
        m = glyph.Router()
        @m.default()
        class Test(glyph.r):
            def __init__(self, _value=0):
                self._value = int(_value)
            @glyph.inline()
            def value(self):
                return self._value

            @glyph.safe()
            def add2(self):   
                return self._value + 2
        return m

    def testCase(self):
        result = glyph.get(self.endpoint.url)
        self.assertEqual(result.value(), 0)
        self.assertEqual(result.add2(), 2)




class FormObjectTest(ServerTest):

    def router(self):
        m = glyph.Router()
        @m.default()
        class Root(glyph.r):
            def index(self):
                return dict(
                    test = glyph.form(Test)
                )

        @m.add()
        class Test(glyph.r):
            def __init__(self, _value=0):
                self._value = int(_value)

            @glyph.inline()
            def value(self):
                return self._value

        return m

    def testCase(self):
        root = glyph.get(self.endpoint.url)
        result = root.test(0)
        self.assertEqual(result.value(), 0)
        result = root.test(2)
        self.assertEqual(result.value(), 2)

class PersistentObjectTest(ServerTest):

    def router(self):
        m = glyph.Router()
        @m.default()
        class Root(glyph.r):
            def index(self):
                return dict(
                    test = glyph.form(Test)
                )

        @m.add()
        class Test(glyph.PersistentResource):
            def __init__(self, _value=0):
                self._value = int(_value)

            @glyph.inline()
            def value(self):
                return self._value

            def index(self):
                return {'self': glyph.link(self)}


        return m

    def testCase(self):
        root = glyph.get(self.endpoint.url)
        result_a = root.test(0)
        self.assertEqual(result_a.value(), 0)
        result_b = root.test(0)
        self.assertEqual(result_b.value(), 0)
        self.assertNotEqual(result_a.self.url(), result_b.self.url())

class DefaultPersistentObjectTest(ServerTest):

    def router(self):
        m = glyph.Router()
        @m.default()
        class Test(glyph.PersistentResource):
            def __init__(self, _value=0):
                self._value = int(_value)

            @glyph.inline()
            def value(self):
                return self._value

            @glyph.redirect()
            def make(self, value):
                return Test(value)

            def index(self):
                return {'self': glyph.link(self)}


        return m

    def testCase(self):
        result_a = glyph.get(self.endpoint.url)
        self.assertEqual(result_a.value(), 0)
        result_b = result_a.make(0)
        self.assertEqual(result_b.value(), 0)
        self.assertNotEqual(result_a.self.url(), result_b.self.url())

class VerbTest(ServerTest):

    def router(self):
        m = glyph.Router()
        @m.default()
        class Test(glyph.r):
            def POST(self):   
                return 0

            def index(self):
                return {'make':glyph.form(Test), 'zero': glyph.form(self)}
        return m

    def testCase(self):
        result = glyph.get(self.endpoint.url)
        self.assertEqual(result.zero(), 0)
        result = result.make()
        self.assertEqual(result.zero(), 0)
if __name__ == '__main__':
    unittest2.main()
