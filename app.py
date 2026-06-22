"""
================================================================================
 AgileMind · Backend Flask (app factory)
 Júlio Cesar de Souza Silva

 create_app() monta a aplicação injetando um Container de dependências:
   - em produção: adaptadores reais do Supabase (build_container)
   - em testes: fakes em memória, passados via create_app(container=...)

 Blueprints:
   - auth   : /admin/create-user, /admin/deactivate-user, /login, /logout
   - legacy : RAG sobre PDF (a migrar nas Fases 3–5)
================================================================================
"""
from flask import Flask

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import Config


def create_app(config: Config | None = None, container=None) -> Flask:
    config = config or Config()

    if container is None:
        from container import build_container
        container = build_container(config)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.FLASK_SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
    app.config["CONTAINER"] = container

    from flask import jsonify

    from services.errors import DomainError

    @app.errorhandler(DomainError)
    def _on_domain_error(e: DomainError):
        return jsonify({"error": e.message}), e.status

    from admin.routes import bp as admin_bp
    from auth.routes import bp as auth_bp
    from routes.legacy import bp as legacy_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(legacy_bp)
    return app


if __name__ == "__main__":
    application = create_app()
    print("\n" + "=" * 60)
    print("  AgileMind · Agente de Análise de Squads")
    print("  http://localhost:5000")
    print("=" * 60 + "\n")
    application.run(debug=True, port=5000, threaded=True)
