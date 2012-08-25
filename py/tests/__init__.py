import unittest2
import hyperglyph as glyph
import datetime
import collections

from cStringIO import StringIO
from io import BytesIO



class EncodingTest(unittest2.TestCase):
    def testCase(self):
        cases = [
            1,
            1.0,
            "foo",
            u"bar",
            [],
            ['a',1,[2]],
            collections.OrderedDict([('a', 1), ('b',2)]),
            None,
            True,
            False,
            {'a':1},
            set([1,2,3]),
            glyph.utcnow(),
            datetime.timedelta(days=5, hours=4, minutes=3, seconds=2),
        ]
        for c in cases:
            self.assertEqual(c, glyph.parse(glyph.dump(c)))

class BlobEncodingTest(unittest2.TestCase):
    def testCase(self):
        s = "Hello, World"
        a = glyph.blob(s)
        b = glyph.parse(glyph.dump(a))

        self.assertEqual(s, b.fh.read())

        s = "Hello, World"
        a = glyph.blob(BytesIO(s))
        b = glyph.parse(glyph.dump(a))

        self.assertEqual(s, b.fh.read())


class ExtTest(unittest2.TestCase):
    def testCase(self):
        cases = [
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
            @glyph.embed()
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

        @m.add()
        class Test(glyph.r):
            def __init__(self, _value=0):
                self._value = int(_value)

            @glyph.embed()
            def value(self):
                return self._value

        return m

    def testCase(self):
        root = glyph.get(self.endpoint.url)
        result = root.Test(0)
        self.assertEqual(result.value(), 0)
        result = root.Test(2)
        self.assertEqual(result.value(), 2)

class PersistentObjectTest(ServerTest):

    def router(self):
        m = glyph.Router()

        @m.add()
        class Test(glyph.PersistentResource):
            def __init__(self, _value=0):
                self._value = int(_value)

            @property
            def self(self):
                return glyph.link(self)
            
            @property
            def value(self):
                return self._value


        return m

    def testCase(self):
        root = glyph.get(self.endpoint.url)
        result_a = root.Test(0)
        self.assertEqual(result_a.value, 0)
        result_b = root.Test(0)
        self.assertEqual(result_b.value, 0)
        self.assertNotEqual(result_a.self.url(), result_b.self.url())

class DefaultPersistentObjectTest(ServerTest):

    def router(self):
        m = glyph.Router()
        @m.default()
        class Test(glyph.PersistentResource):
            def __init__(self, _value=0):
                self._value = int(_value)

            @glyph.embed()
            def value(self):
                return self._value

            @glyph.redirect()
            def make(self, value):
                return Test(value)

            @property
            def self(self):
                return glyph.link(self)


        return m

    def testCase(self):
        result_a = glyph.get(self.endpoint.url)
        self.assertEqual(result_a.value(), 0)
        result_b = result_a.make(0)
        self.assertEqual(result_b.value(), 0)
        self.assertNotEqual(result_a.self.url(), result_b.self.url())

class HiddenMethodTest(ServerTest):
    def router(self):
        m = glyph.Router()
        @m.default()
        class Test(glyph.r):

            @glyph.hidden()
            def nope(self):
                return "Nope"
        return m

    def testCase(self):
        result = glyph.get(self.endpoint.url)
        with self.assertRaises(StandardError):
            self.result.nope()

class SpecialMethodTest(ServerTest):
    def router(self):
        m = glyph.Router()
        @m.default()
        class Test(glyph.r):
            @classmethod
            def clsm(cls):   
                return "Hello"

            @staticmethod
            def static(self):
                return "World"
        return m

    def testCase(self):
        result = glyph.get(self.endpoint.url)
        with self.assertRaises(AttributeError):
            self.result.clsm()
        with self.assertRaises(AttributeError):
            self.result.static()

class VerbTest(ServerTest):

    def router(self):
        m = glyph.Router()
        @m.default()
        class Test(glyph.r):
            def POST(self):   
                return 0

            def GET(self):
                return {'make':glyph.form(Test), 'zero': glyph.form(self)}
        return m

    def testCase(self):
        result = glyph.get(self.endpoint.url)
        self.assertEqual(result['zero'](), 0)
        result = result['make']()

class FunctionTest(ServerTest):

    def router(self):
        m = glyph.Router()
        @m.add()
        def foo(a,b):
            return a+b

        @m.add()
        def bar(a,b):
            return a*b

        @m.add()
        def baz(a,b,c):
            return a,b,c



        return m

    def testCase(self):
        root = glyph.get(self.endpoint.url)
        self.assertEqual(root.foo(1,1), 2)
        self.assertEqual(root.bar(1,1), 1)
        self.assertEqual(root.baz(1,2,3), [1,2,3])
        self.assertEqual(root.baz(c=3,b=2,a=1), [1,2,3])
        self.assertEqual(root.baz(1,c=3,b=2), [1,2,3])

class FunctionRedirectTest(ServerTest):

    def router(self):
        m = glyph.Router()

        @m.add()
        @glyph.safe()
        def bar():
            return 123

        @m.add()
        @glyph.redirect()
        def foo():
            return bar


        return m

    def testCase(self):
        root = glyph.get(self.endpoint.url)
        self.assertEqual(root.foo(), 123)

class PropertyAsInstanceValue(ServerTest):

    def router(self):
        m = glyph.Router()

        @m.default()
        class R(glyph.Resource):
            @property
            def foo(self):
                return 123


        return m

    def testCase(self):
        root = glyph.get(self.endpoint.url)
        self.assertEqual(root.foo, 123)

class Inline(ServerTest):
    def setUp(self):
        ServerTest.setUp(self)

    def router(self):
        m = glyph.Router()
        @m.add()
        def pair():
            return Other(0), Other(1)

        @m.add()
        def unit():
            return pair

        @m.add()
        class Other(glyph.r):
            def __init__(self, v=0):
                self.v = v
        return m

    def testCase(self):
        index = glyph.get(self.endpoint.url)


        a,b = index.unit()()
        self.assertEqual(a.v, 0)
        self.assertEqual(b.v, 1)

if __name__ == '__main__':
    unittest2.main()

class BlobReturnAndCall(ServerTest):

    def router(self):
        m = glyph.Router()

        @m.default()
        class R(glyph.Resource):
            def do_blob(self, b):
                s = b.fh.read()
                c = b.content_type
                return glyph.blob(BytesIO(s.lower()), content_type=c)


        return m

    def testCase(self):
        root = glyph.get(self.endpoint.url)
        b = glyph.blob(BytesIO("TEST"), content_type="Test")
        b2 = root.do_blob(b)
        self.assertEqual(b2.fh.read(), "test")
        self.assertEqual(b2.content_type, "Test")
