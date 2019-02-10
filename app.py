'''
verison5: 结合version2和version4

在version2中我们增加了：
1.get，post两个装饰器
2.add_route ,add_routes两个方法

在version4中我们增加了：
1.RequestHandler类
2.has_named_kw_args(fn)， has_var_kw_arg(fn)， has_request_arg(fn)， get_required_kw_args(fn)，get_named_kw_args(fn)五个方法

这些方法都是关于request处理的，我们可以把他们放到一个单独的模块coroweb.py

所以我们可以把文件分成三部分
1.所有的handler函数在handlers.py
2.所有的request处理的放到coroweb.py
3.剩下的放在app.py
'''

from aiohttp import web
import handlers
from coroweb import *

async def init(loop):
    app = web.Application(loop=loop)
    add_routes(app,'handlers')
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    print('Server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
