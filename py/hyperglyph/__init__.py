""" hyperglyph - duck typed ipc """
"""
Copyright (c) 2012 Thomas Figg (tef)
Copyright (c) 2011-2012 Hanzo Archives Ltd

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included 
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


from .data import CONTENT_TYPE, dump, dump_iter, parse, get, form, link, utcnow, embedlink, error
from .encoding import blob
from .resource.handler import safe, embed, redirect, hidden
from .resource.transient import TransientResource
from .resource.persistent import PersistentResource
from .resource.base import ClassMapper
from .resource.router import Router
from .server import  Server

__all__ = [
    'CONTENT_TYPE','Server','redirect','hidden',
    'get', 'Router','Resource','r', 'safe', 'embed', 'utcnow',
    'parse','dump','form','link','embedlink', 'blob', 'error',
    'TransientResource', 'PersistentResource', 
    'ClassMapper',
]

r = Resource = TransientResource

