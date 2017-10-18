#-*- coding:utf-8 -*-

import getpass
import os
from io import BytesIO

from flowlight.model.group import Cluster
from flowlight.core.setting import Setting


class API:
    """ Simple HTTP API Server to run command on machines by url.
    """
    PORT = Setting.API_PORT
    __doc__ = 'Usage:: http://0.0.0.0:{}/<machines>/<command>'.format(Setting.API_PORT)

    @classmethod
    def serve(cls):
        from http.server import SimpleHTTPRequestHandler, HTTPServer
        from socketserver import ThreadingMixIn
        from urllib.request import unquote
        from urllib.parse import urlparse, parse_qs
        class Server(ThreadingMixIn, HTTPServer): pass
        class Handler(SimpleHTTPRequestHandler): pass
        def _handle_json(self, responses):
            import json
            res = []
            for r in responses:
                res.append({
                    'host': str(r.target),
                    'result': r.result.decode()
                })
            res = json.dumps(res)
            self.send_header('Content-Type', 'application/json')
            return res

        def do_GET(self):
            try:
                url = urlparse(self.path)
                qs = parse_qs(url.query)
                paths = url.path.split('/', 2)
                machines, cmd = paths[1], "".join(paths[2:]) if len(paths) >= 3 else None
                if cmd is None:
                    raise Exception('Command is none.')
                hosts = machines.split(',')
                cluster = Cluster(hosts)
                cluster.enable_connection()
                responses = cluster.run(unquote(cmd))
                self.send_response(200)
                res = _handle_json(self, responses)
                self.end_headers()
                self.copyfile(BytesIO(bytes(res, 'utf-8')), self.wfile)
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.copyfile(BytesIO(bytes(cls.__doc__, 'utf-8')), self.wfile)
        Handler.do_GET = do_GET
        server = Server(('127.0.0.1', cls.PORT), Handler)
        print('FlowLight API serve on {port}... \n {usage}'.format(port=cls.PORT, usage=cls.__doc__))
        server.serve_forever()

api_serve = API.serve

