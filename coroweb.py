
import functools

#1.写get装饰器把handlers对应的get方法和path转化成handler函数的__method__,__path__属性
def get(path):
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

#2.写post装饰器把handlers对应的post方法和path转化成handler函数的__method__,__path__属性
def post(path):
    '''
    Define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

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
    app.router.add_route(method, path,RequestHandler(app, fn))

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
from aiohttp import web
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
            return e

#RequestHandler class end