"""Keep legacy CLI unit tests off the user's running Web service.

The transport returns 401, never fabricated successful platform data.
Real authenticated HTTP coverage remains in stage1–stage6.
"""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import logging
from queue import Queue
import threading

import pytest


@pytest.fixture(scope='session')
def denied_cli_transport():
    class Denied(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error":"Authentication required"}')

        do_POST = do_GET

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Denied)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield 'http://127.0.0.1:' + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


@pytest.fixture(autouse=True)
def isolate_legacy_cli_options(request, monkeypatch):
    if request.cls is None or request.cls.__name__ != 'TestSpiderFootCli':
        return
    from sfcli import SpiderFootCli
    options = deepcopy(request.cls.cli_default_options)
    options['cli.server_baseurl'] = request.getfixturevalue('denied_cli_transport')
    monkeypatch.setattr(SpiderFootCli, 'ownopts', options)


@pytest.fixture(autouse=True)
def isolate_legacy_ui_log_queue(request, monkeypatch):
    if request.cls is None or request.cls.__name__ != 'TestSpiderFootWebUi':
        yield
        return
    from sfwebui import SpiderFootWebUi
    original = SpiderFootWebUi.__init__
    logger = logging.getLogger('spiderfoot')
    previous = list(logger.handlers)
    logger.handlers.clear()

    def initialize(self, *args, **kwargs):
        # Unit rendering tests have no log-consumer process. Use the public
        # injected queue boundary instead of leaking multiprocessing listeners.
        if len(args) < 3 and kwargs.get('loggingQueue') is None:
            kwargs['loggingQueue'] = Queue()
        return original(self, *args, **kwargs)

    monkeypatch.setattr(SpiderFootWebUi, '__init__', initialize)
    try:
        yield
    finally:
        logger.handlers[:] = previous
