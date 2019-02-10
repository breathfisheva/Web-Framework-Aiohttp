from aiohttp import web
from coroweb import *
import asyncio


#3.给每个handler函数增加__method__属性和__route__属性。
@get('/')
async def index(request):
    await asyncio.sleep(0.5)
    return web.Response(body=b'<h1>Index</h1>', content_type='text/html')

@get('/hello/{name}')
async def hello(request, *, name):
    await asyncio.sleep(0.5)
    text = '<h1>hello, %s!</h1>' % request.match_info['name']
    return web.Response(body=text.encode('utf-8'), content_type='text/html')