'''
a simple aiohttp as server example

1.A request handler must be a coroutine that accepts a Request instance as its only parameter and returns a Response instance
我们这里创建了两个request handler，分别是
index(request)
hello(request)

2.create an Application instance
app = web.Application(loop=loop)

3.register the request handler on a particular HTTP method and path:
app.router.add_route('GET', '/', index)
app.router.add_route('GET', '/hello/{name}', hello)
add_route方法会把request请求的值作为参数传给index，hello方法

4.访问
http://127.0.0.1:9000
http://127.0.0.1:9000/hello/lucy
'''


import asyncio
from aiohttp import web

async def index(request):
    await asyncio.sleep(0.5)
    return web.Response(body=b'<h1>Index</h1>', content_type='text/html')

async def hello(request):
    await asyncio.sleep(0.5)
    text = '<h1>hello, %s!</h1>' % request.match_info['name']
    return web.Response(body=text.encode('utf-8'), content_type='text/html')

async def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    app.router.add_route('GET', '/hello/{name}', hello)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    print('Server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()