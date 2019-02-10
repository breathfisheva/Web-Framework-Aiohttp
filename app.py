'''
version4： 优化RequestHandler类

1.之前只考虑get方法，没有考虑post方法，区分处理get，post方法，并把从他们中获取的值赋给kw （kw是一个dict）
------------------------------------------------------------------------------------------------------------------------
1.1 获取post方法里的数据 - 一般post的数据都是放到body里
To access form data with "POST" method use Request.post() or Request.multipart().

Request.post() accepts both 'application/x-www-form-urlencoded' and 'multipart/form-data' form’s data encoding .
It stores files data in temporary directory.
If client_max_size is specified post raises ValueError exception.
For efficiency use Request.multipart(), It is especially effective for uploading large files (File Uploads).

-》也就是，如果是request.content_type是application/x-www-form-urlencoded' 或者 'multipart/form-data ：
用request.post方法获取body数据

-》如果request.content_type是application/json，则把request转成json数据类型
用request.json方法（Read request body decoded as json.）

1.2 获取get方法里的数据 - 一般get的数据都是放在query_string里
-》用request.query_string 获取

-》然后用urllib.parse.parse_qs函数分析URL中query组件的参数，返回一个key-value对应的字典格式
关于urllib.parse.parse_qs的例子：

import urllib.parse
print(urllib.parse.parse_qs("FuncNo=9009001&username=1"))
输出结果：
{'FuncNo': ['9009001'], 'username': ['1']}


2.path路径里可能会有一些变量，获取path的变量值，并赋给kw （kw是一个dict）
------------------------------------------------------------------------------------------------------------------------
比如我们的hello方法对应的path是'/hello/{name}'，里面的name就是变量

-》我们用request.match_info方法获取变量值
Resource may have variable path also. For instance, a resource with the path '/a/{name}/c' would match all incoming requests with paths such as '/a/b/c', '/a/1/c', and '/a/etc/c'.

A variable part is specified in the form {identifier}, where the identifier can be used later in a request handler to access the matched value for that part. This is done by looking up the identifier in the Request.match_info mapping:

@routes.get('/{name}')
async def variable_handler(request):
    return web.Response(
        text="Hello, {}".format(request.match_info['name']))

3.代码中涉及到好几处的函数参数种类判断以及函数参数名提取，把他们独立出来处理
------------------------------------------------------------------------------------------------------------------------
-》函数参数种类判断
has_named_kw_args(fn) 是否有命名关键字参数keyword_only
has_var_kw_arg(fn) 是否有关键字参数var_keyword
has_request_arg(fn) 是否有参数名为request的参数

-》函数参数名提取
get_required_kw_args(fn) 没有默认值，必须传入值的命名关键字参数
get_named_kw_args(fn)所有的命名关键字参数名，包括有默认值的

-》用处
1):if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
只要有这三个中任意一种参数，我们就需要从request中获取参数值传入。

2):if not self._has_var_kw_arg and self._named_kw_args:
如果没有关键字参数，可是有命名关键字参数
把命名关键字参数，和kw（从requst中获得数据）进行对比，去除kw中不属于命名关键字参数的部分。也就是kw只留handler函数需要的参数值。

3):if self._has_request_arg:
如果有参数名为request的参数，则传给kw

4): if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
如果有需要传入值的参数，可是kw中却不存在这个参数对应的值，则抛出错误

'''
import asyncio
from aiohttp import web

# 1.handler 函数
async def index(request):
    await asyncio.sleep(0.5)
    return web.Response(body=b'<h1>Index</h1>', content_type='text/html')

async def hello(request, *, name):  #需要是async，否则报错object bytes can't be used in 'await' expression
    await asyncio.sleep(0.5)
    text = '<h1>hello, %s!</h1>' % name
    return web.Response(body=text.encode('utf-8'), content_type='text/html')

# 2.RequestHandler class start
from urllib import parse
import inspect,logging

#2.1 把必须传入值的命名关键字参数名放到一个tuple里返回
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

#2.2 把所有命名关键字参数名放到一个tuple里返回 （包括有些以及由默认值的命名关键字参数）
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

#2.3 handler函数的参数中是否有命名关键字参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

#2.4 handler函数的参数中是否有可变参数
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

#2.5 handler函数中是否有一个名为request的参数
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

# 3.定义RequestHandler类
class RequestHandler(object):

#3.1 初始化类，把web.application实例以及handler函数传进来
    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

#3.2 定义一个__call__方法，因为add_route里需要它是一个coroutine，而且只有一个参数request。所以把它写成coroutine，await handler函数
#调用add_route的时候会把request值传给__call__
    async def __call__(self, request):
        #3.2.1 初始化kw，之后会把所有的request包含的data，path里的变量信息，还有request值都传给kw，kw是一个dict，然后kw只留handler函数需要的值，把kw传给handler函数执行
        kw = None
        #3.2.2 如果有可变参数，命名关键字参数，或者有必须传入值的参数，则从request中获取data
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            #判断是否是Post方法
            if request.method == 'POST':
                #1.如果没有content_type则报错
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')

                #2.如果content_type是json类型，则把request转成json类型赋值给kw
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params

                #3.如果是'application/x-www-form-urlencoded'或'multipart/form-data'，则把post的body的data传给kw
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)

            #判断是否是get方法，则从query_string中获取值转换成键值对，然后赋值给kw
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]

        #3.2.3 如果request里没有data，则把request的match_info（也就是变量信息）传给kw
        if kw is None:
            kw = dict(**request.match_info)

        #3.2.4 如果request里有data，则对比kw里的变量名和handler函数里的参数名，只留handler函数需要的参数值，然后把request的match_info（也就是变量信息）传给kw
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                # remove all unamed kw:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v

        #3.2.5 如果handler函数有参数名为request，则把add_route传给__call__的request放入kw
        if self._has_request_arg:
            kw['request'] = request

        #3.2.6 如果有必须传值的参数，可是在kw中却找不到对应的值则报错
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            #3.2.7 把kw作为参数传入，调用handler函数，返回函数返回值。
            #注意：因为kw是字典，所以传入需要两个*
            #注意：这里要用await
            r = await self._func(**kw)
            return r
        # except APIError as e:
        #     return dict(error=e.error, data=e.data, message=e.message)
        except Exception as e:
            return dict(error=e.error, data=e.data, message=e.message)

#RequestHandler class end

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