import logging
import socket
import tornado
import tornado.gen
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.web
import sys
import urlparse

class RequestHandler(tornado.web.RequestHandler):

    def initialize(self, proxy_to, ca_file):
        self.proxy_to = urlparse.urlparse(proxy_to)
        self.ca_file = ca_file

    @tornado.web.asynchronous
    @tornado.gen.engine
    def handle_request(self):
        try:
            logging.info("proxying request %s to %s" % (self.request.path, self.proxy_to.netloc))

            request = self._build_request()

            http_client = tornado.httpclient.AsyncHTTPClient(io_loop=tornado.ioloop.IOLoop.instance())
            response = yield tornado.gen.Task(http_client.fetch, request)

            self._send_response(response)
        except Exception as e:
            logging.exception("Unexpected error:")

    def _build_request(self):
        uri = urlparse.urlunparse([self.proxy_to.scheme, self.proxy_to.netloc, self.request.path, None, self.request.query, None])

        headers = self.request.headers.copy()
        del headers['Host']

        if self.request.method == "GET":
            body = None
        else:
            body = self.request.body

        request = tornado.httpclient.HTTPRequest(
            uri,
            ca_certs = self.ca_file,
            method = self.request.method,
            headers = headers,
            body = body
        )
        return request

    def _send_response(self, response):
        message = response.body
        self.set_status(response.code)
        headers = response.headers.copy()
        if 'Transfer-Encoding' in headers:
            del headers['Transfer-Encoding']

        for header, value in headers.iteritems():
            self.set_header(header, value)
        self.set_header("X-Proxy-Server", socket.gethostname())
        self.write(message)
        self.finish()

    get = post = put = delete = handle_request
