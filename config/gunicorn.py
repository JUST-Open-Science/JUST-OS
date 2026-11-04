# -*- coding: utf-8 -*-

import logging
import os

from distutils.util import strtobool

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
accesslog = "-"
errorlog = "-"
capture_output = True
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = (
    "%(h)s %(l)s %(u)s %(t)s '%(r)s' %(s)s %(b)s '%(f)s' '%(a)s' in %(D)sµs"  # noqa: E501
)

workers = int(os.getenv("WEB_CONCURRENCY", 1)) # conservative default to prevent ooms
threads = int(os.getenv("PYTHON_MAX_THREADS", 1))

reload = bool(strtobool(os.getenv("WEB_RELOAD", "false")))

timeout = int(os.getenv("WEB_TIMEOUT", 120))


def post_fork(server, worker):
    """Send application log records through Gunicorn to container stdout."""
    root_logger = logging.getLogger()
    root_logger.handlers = server.log.error_log.handlers
    root_logger.setLevel(server.log.loglevel)
