'''
之前我们的handler函数要传给add_route，add_route要求handler是coroutine，
可是我们现在用RequestHandler封装了handler函数，在RequestHandler里我们await了handler方法，所以handler函数可以不需要是coroutine
'''

from aiohttp import web
from coroweb import *
import asyncio


#3.给每个handler函数增加__method__属性和__route__属性。
@get('/')
def index(request):
    return web.Response(body=b'<h1>Index</h1>', content_type='text/html')

@get('/hello/{name}')
def hello(request, *, name):
    text = '<h1>hello, %s!</h1>' % request.match_info['name']
    return web.Response(body=text.encode('utf-8'), content_type='text/html')