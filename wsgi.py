"""
Entry point de produção (gunicorn). Aplica ProxyFix para que o Flask enxergue
o esquema HTTPS repassado pelo proxy do Railway — assim os cookies de sessão
ficam Secure e a detecção de HTTPS funciona (AUTH-07 / INF-07).

Uso (Procfile): gunicorn wsgi:app
"""
from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app

app = create_app()
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
