from os import sched_getaffinity
from ssl import SSLContext, PROTOCOL_TLS_SERVER
from socketserver import ThreadingMixIn
from http import server as http_server
from concurrent.futures import ThreadPoolExecutor

from .handler import HTTPHandler
from .logger import logger


class PooledHTTPServer(ThreadingMixIn, http_server.HTTPServer):
    def __init__(
        self, server_address, RequestHandlerClass, max_workers, bind_and_activate=True
    ):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        self.pool = ThreadPoolExecutor(max_workers=max_workers)

    def process_request(self, request, client_address):
        # NOTE: for each request, we process it using thread-pool in parallel
        self.pool.submit(self.process_request_thread, request, client_address)


class HTTPServer:
    def __init__(
        self,
        host: str,
        port: int,
        ssl_enabled: bool,
        ssl_certfile: str,
        ssl_keyfile: str,
        max_workers: int,
        verbose: bool = False,
    ):
        self.host = host
        self.port = port
        self.ssl_enabled = ssl_enabled
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        if max_workers <= 0:
            max_workers = len(sched_getaffinity(0))
        self.max_workers = max_workers
        if verbose:
            logger.setLevel("DEBUG")

    def serve_forever(self):
        # TODO: server side support per clinet HTTP keep-alive
        server = PooledHTTPServer(
            (self.host, self.port), HTTPHandler, max_workers=self.max_workers
        )
        if self.ssl_enabled:
            context = SSLContext(PROTOCOL_TLS_SERVER)
            context.load_cert_chain(
                certfile=self.ssl_certfile, keyfile=self.ssl_keyfile
            )
            server.socket = context.wrap_socket(server.socket, server_side=True)
        server.allow_reuse_address = True
        server.serve_forever()
