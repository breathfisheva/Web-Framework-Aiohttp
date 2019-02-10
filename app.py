'''
version2 : 使用add_routes方法自动注册所有的handler

#问题：
前面我们用add_route方法把request handler和对应的HTTP方法（get，post），路径对应起来，并且把request值传给request handler 函数。
这就意味着，每增加一个新的request handler函数就要写一次add_route，比如新增一个hello函数则代码：
app.router.add_route('GET', '/', index)
app.router.add_route('GET', '/hello/{name}', hello)

如果有很多个request handler函数，那就要写很多次add_route

#解决思路：
把所有的request handler函数写到一个module里【handlers.py】。
然后写一个函数add_routes(app, module_name)遍历handlers模块，把里面的所有的request handler函数都注册一遍。
这样在主程序中只需要调用一次add_routes方法就注册了所有的URL函数的方法。

#具体步骤：
1.把所有的request handlers函数放到handlers.py模块里。
1.1 为了后面方便获取request handler函数的HTTP方法和path，我们定义get和post装饰器，把handlers对应的HTTP方法和path转化成request handler函数的__method__,__path__属性

2.写一个add_routes函数把handlers模块里的所有handler函数遍历一遍

3.写一个add_route方法，封装之前的app.router.add_route('GET', '/', index)
让每次不需要hard code写入GET方法和path，只需要读取index函数的__method__和__route__

4.在init中调用add_routes方法把所有的handler函数和对应的HTTP方法，path注册一遍。
'''


# 2.写一个add_routes函数把handlers模块里的所有handler函数遍历一遍
def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        # mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
        mod = __import__(module_name, fromlist=True)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)

# 3.写一个add_route方法，封装之前的app.router.add_route('GET', '/', index)，让每次不需要hard code写入GET方法和path，只需要读取index函数的__method__和__route__
import asyncio,inspect,logging
def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path,fn)

#4.在init中调用add_routes方法把所有的handler函数和对应的HTTP方法，path注册一遍。
from aiohttp import web
import handlers
async def init(loop):
    app = web.Application(loop=loop)
    add_routes(app,'handlers')
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    print('Server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()