import multiprocessing

# Gunicorn configuration file
# Reference: https://docs.gunicorn.org/en/stable/configure.html

# Bind to 0.0.0.0:8000 for Docker/Proxy
bind = "0.0.0.0:8000"

# Number of worker processes
# Formula: (2 x $num_cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class (sync is usually fine for Django, but gevent/eventlet are options)
worker_class = "sync"

# Timeout for workers
timeout = 120

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Security: Don't reveal server info
server_tokens = "off"

# Performance: Preload app code before workers are forked
preload_app = True
