'''
verison6: 使用middleware统一处理response

#问题：
我们之前的handler函数，都要处理reponse，把结果转换为web.Response对象然后再返回。这里就涉及到(1):给response 的body赋值；(2):定义content_type；比如：
def index(request):
    return web.Response(body=b'<h1>Index</h1>', content_type='text/html')

这样如果我们有很多个handler函数，则每一个函数都要处理一遍。

#思路：
我们使用middleware把通用的功能从每个URL处理函数中拿出来，集中放到一个地方，我们这里用middleware把返回值转换为web.Response对象再返回

#步骤：
1. 改进handler函数，不需要做转换response的动作。这样handler函数可能返回的类型有。
    1.1 返回的是web.StreamResponse
    1.2 bytes类型
    1.3 str类型 （要注意有没有重定向 ，字符串中是否含有redirect）
    1.4 dict类型
        1.4.1 如果dict类型里的__template__有值，则html文件即是response的body。比如
        def manage_users(*, page='1'):
            return {
                '__template__': 'manage_users.html',
                'page_index': get_page_index(page)
            }
        1.4.2 如果dict类型里的__template__没有值
    1.5 int类型
    1.6 tuple类型
    1.7 其他

2. 定义一个response_factory(app, handler)函数来处理不同的handler函数的返回值，把他们都转换成web.Response对象
    1.1 web.StreamResponse --》 直接返回
    1.2 bytes类型 --》 把bytes值传给body， content_type = 'application/octet-stream'
    1.3 str类型
        --》 如果有redirect，则重定向
        --》 str转成bytes传给body，content_type = 'text/html;charset=utf-8'
    1.4 dict类型
        --》 __template__有指向某个html文件， 把html给body， content_type = 'text/html;charset=utf-8'
        --》 __template__没有值，则把dict的值变成json，然后content_type = 'application/json;charset=utf-8'
    1.5 int类型 --》 返回状态码
    1.6 tuple类型 --》 返回状态码和状态说明短语
    1.7 其他 --》转成str，然后编码utf-8，content_type = 'text/plain;charset=utf-8' ，强制转为网页

3. 在web.Application实例中使用middlerware
app = web.Application(loop=loop, middlewares=[response_factory])
'''

from aiohttp import web
import handlers
from coroweb import *
import json

async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        #1. 把handler的返回值赋值给r
        r = await handler(request)

        #2. 如果handler函数的返回是web.StreamResponse类型，则直接返回
        if isinstance(r, web.StreamResponse):
            return r

        #3. 如果handler函数的返回是bytes类型，则把response的content_type定义为application/octet-stream，然后返回
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp

        #4. 如果handler函数的返回是str类型，则把response的content_type定义为text/html;charset=utf-8，然后返回
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:]) #取redirect:之后的内容
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp

        #5. 如果handler函数的返回是dict类型，
        #5.1 则获取html模板__template__.然后把html模板作为response的body，并且把response的content_type定义为text/html;charset=utf-8，然后返回
        #5.2 如果没有html模板，则把handler返回值定义成json，然后把content_type定义为application/json;charset=utf-8
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp

        #6. 如果handler函数的返回是int类型，并且范围在100-600，则直接返回r作为状态码
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(status=r)

        #7. 如果handler函数的返回是tuple类型，并且tuple里有两个元素，其中一个元素是整数范围在10-600，则返回状态码和说明
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(status=t, body=str(m))

        #8. 如果handler函数的返回都不是上面的类型，则指定返回是一个网页类型
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


async def init(loop):
    app = web.Application(loop=loop, middlewares=[response_factory])#response_factory指定返回类型
    add_routes(app,'handlers')
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    print('Server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
