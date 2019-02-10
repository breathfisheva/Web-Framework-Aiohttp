'''
verison3: 使用一个RequestHandler类来统一处理request handler函数关于提取request信息的需求，这样handler函数只需要直接写业务有关的代码即可。
需要注意的是，这样处理后handler函数的参数名就不能随便定义，
必须和request里对应的名字一样，另外如果需要request请求作为参数，就必须写成request，否则RequestHandler类认不出来。


#问题：
request handler 函数，主要就是从request中获取需要的参数值，然后进行处理后返回一个web.response对象。

比如我们定义的hello方法，里面就需要从request里提取match_info中name的值。
text = '<h1>hello, %s!</h1>' % request.match_info['name']
也就是说，如果我们有很多个request handler函数，并且不同的handler函数需要提取不同的request里的信息，那每个handler函数都需要写一堆提取request里信息的代码

#解决思路：
定义一个函数，输入是不同的handler函数，然后根据不同handler函数的需求提取需要的request的信息，然后作为参数传给handler函数，输出是handler函数的返回值

#具体步骤：
1.为了表明handler函数需要哪些request的值，我们就把需要的值的名字作为handler函数的参数名。比如hello函数就把name作为参数名。
async def hello(request, *, name): #需要是async，否则报错object bytes can't be used in 'await' expression
await asyncio.sleep(0.5)
text = '<h1>hello, %s!</h1>' % name
return web.Response(body=text.encode('utf-8'), content_type='text/html')

2.定义一个RequestHandler类，为什么用类，我们之后会讲解。然后这个类的传入的参数是handler函数，遍历这个函数，知道他需要哪些参数，把这些参数存到args里，args是一个tuple
args = []
params = inspect.signature(self.fn).parameters
for name, param in params.items():
if param.kind == inspect.Parameter.KEYWORD_ONLY:
args.append(name)
args = tuple(args)

3.handler函数可能需要的参数值下面几种，把这些值全部赋值给kw，kw是一个dict（参数名和对应的参数值）：

参数来自于reqeust.query_string
参数来自于request.match_info
request参数

4.把kw的值和args比较，如果是handler函数需要的参数则留下了

5.把kw传给handler函数，返回handler函数的返回值

#说明：
我们之所以选择类，是因为我们将用RequestHandler代替handler传给add_route
app.router.add_route('GET', '/',RequestHandler(app, index))

add_route 方法对它的第三个参数的要求是：
1.需要是coroutine的函数
2.同时只能接收一个参数也就是request

可是我们又需要传入handler函数作为参数，之后才能对不同的handler函数进行处理，所以我们选择用类。
一方面类的__init__方法允许我们传入handler函数作为参数，
另一方面类的__call__方法可以让RequestHandler类像普通handler函数一样接收request参数被调用

async def __call__(self, request): #注意：使用coroutine
r = await self.fn(*args)

'''


import asyncio
from aiohttp import web

async def index(request):
    await asyncio.sleep(0.5)
    return web.Response(body=b'<h1>Index</h1>', content_type='text/html')

async def hello(request, *, name):  #需要是async，否则报错object bytes can't be used in 'await' expression
    await asyncio.sleep(0.5)
    text = '<h1>hello, %s!</h1>' % name
    return web.Response(body=text.encode('utf-8'), content_type='text/html')

from urllib import parse
import inspect
class RequestHandler(object):
    def __init__(self, app, fn):
        self.app = app
        self.fn = fn

    async def __call__(self, request):
        # 1.获取URI函数的所有关键字参数名
        args = []
        params = inspect.signature(self.fn).parameters
        for name, param in params.items():
            if param.kind == inspect.Parameter.KEYWORD_ONLY:
                args.append(name)
        args = tuple(args)

        #定义一个kw是一个dict，初始值为None，用来存放URI的参数以及对应的值
        kw = None

        # 2.从request中获得需要的参数值赋值给kw
        # 2.1 从request中获取所有query string的值 比如/hello?name='jack'， 则得到的kw值为dict{('name':'jack'}
        qs = request.query_string
        if qs:
            kw = dict()
            for k, v in parse.parse_qs(qs, True).items():
                kw[k] = v[0]

        # 2.2 如果query_string为空则获取match_info的值比如/hello/{name}，则得到kw值为dict {('name':'lucy'}
        if kw is None:
            kw = dict(**request.match_info)

        # 3.比较URI函数的需要的参数是否在kw中，如果在则提取出来
        copy = dict()
        for name in args:
            if name in kw:
                copy[name] = kw[name]
        kw = copy

        # 4.判断参数名里有么有request，有的话，把request的值传入
        params = inspect.signature(self.fn).parameters
        for name, param in params.items():
            if name == 'request':
                kw['request'] = request

        # 5. 把参数kw传入，调用URI函数
        r = await self.fn(**kw) #kw是dict则是两个**作为关键字参数
        return r

async def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/',RequestHandler(app, index))
    app.router.add_route('GET', '/hello/{name}', RequestHandler(app, hello))
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    print('Server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()



