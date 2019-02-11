'''
改进handler函数，不需要做转换response的动作。这样handler函数可能返回的类型有。
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
'''

from aiohttp import web
from coroweb import *
import asyncio


#3.给每个handler函数增加__method__属性和__route__属性。
@get('/')
def index(request):
    # return web.Response(body=b'<h1>Index</h1>', content_type='text/html')
    return '<h1>Index</h1>'

@get('/hello/{name}')
def hello(request, *, name):
    text = '<h1>hello, %s!</h1>' % request.match_info['name']
    # return web.Response(body=text.encode('utf-8'), content_type='text/html')
    return text