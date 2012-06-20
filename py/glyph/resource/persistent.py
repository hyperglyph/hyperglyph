from uuid import uuid4 

from .base import ClassMapper, BaseResource
from .handler import redirect

class PersistentMapper(ClassMapper):  
    def __init__(self, prefix, res):
        ClassMapper.__init__(self, prefix, res)
        self.instances = {}
        self.identifiers = {}

    @redirect()
    def POST(self, **args):
        instance = self.res(**args)
        uuid = str(uuid4())
        self.instances[uuid] = instance
        self.identifiers[instance] = uuid
        return instance

    def get_instance(self, uuid):
        return self.instances[uuid]

    def get_repr(self, instance):
        if instance not in self.identifiers:
            uuid = str(uuid4())
            self.instances[uuid] = instance
            self.identifiers[instance] = uuid
        else:
            uuid = self.identifiers[instance]
        return uuid

class PersistentResource(BaseResource):
    __glyph__ = PersistentMapper

