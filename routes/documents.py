"""
Rotas de documentos (RAG) — migradas para Supabase Storage + Postgres, por
usuário e com visibilidade. Sem estado global: cada /chat informa o document_id,
e o servidor valida o acesso pelo token (isolamento entre usuários).
"""
from __future__ import annotations

import json
import uuid

from flask import (
    Blueprint, Response, current_app, g, jsonify, redirect,
    render_template, request, stream_with_context, url_for,
)
from werkzeug.utils import secure_filename

from auth.routes import current_user_id, login_required
from services import rag

bp = Blueprint("documents", __name__)


def _c():
    return current_app.config["CONTAINER"]


def _sse(obj) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def _can_read(doc, user_id) -> bool:
    return doc and (doc["owner_user_id"] == user_id or doc["visibility"] == "public")


# ── Página ─────────────────────────────────────────────────────────────
@bp.route("/")
def index():
    if not current_user_id():
        return redirect(url_for("auth.login_page"))
    return render_template("index.html")


# ── Upload ─────────────────────────────────────────────────────────────
@bp.post("/upload")
@login_required
def upload():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400          # UP-04
    file = request.files["file"]
    fname = file.filename or ""
    if "." not in fname or fname.rsplit(".", 1)[1].lower() != "pdf":
        return jsonify({"error": "Apenas PDFs são aceitos"}), 400          # UP-03

    alias = (request.form.get("alias") or "").strip() or fname
    visibility = request.form.get("visibility")
    if visibility not in ("private", "public"):
        # Visibilidade é obrigatória — o upload não prossegue sem a escolha (UP-11).
        return jsonify({"error": "Escolha a visibilidade do documento"}), 400
    data = file.read()
    user_id = g.user_id
    c = _c()

    def process():
        try:
            yield _sse({"type": "progress", "step": "extract", "pct": 10})
            text = rag.extract_pdf_text(data)
            if not text.strip():
                yield _sse({"type": "error", "message": "PDF sem texto extraível"})  # UP-05
                return

            yield _sse({"type": "progress", "step": "classify", "pct": 25})
            sample = " ".join(rag.chunk_text(text[:4000])[:5])[:2000]
            try:
                relevant = c.ai.is_relevant(alias, sample)
            except Exception:
                # Fail-closed (UP-07): se não dá para classificar, bloqueia.
                yield _sse({"type": "rejected", "message": "Não foi possível validar o documento agora. Tente novamente."})
                return
            if not relevant:
                yield _sse({"type": "rejected", "message": "O documento não parece ser de TI ou agilidade. Apenas reports de squads e materiais técnicos são aceitos."})  # UP-02
                return

            yield _sse({"type": "progress", "step": "chunk", "pct": 35})
            chunks = rag.chunk_text(text)

            yield _sse({"type": "progress", "step": "embed", "pct": 55})
            embeddings = c.ai.embed_documents(chunks)

            yield _sse({"type": "progress", "step": "store", "pct": 85})
            storage_path = f"{user_id}/{uuid.uuid4().hex}_{secure_filename(fname)}"
            c.storage.upload(storage_path, data)
            doc_id = c.documents.create(user_id, alias, secure_filename(fname), storage_path, visibility)
            items = [{"chunk_index": i, "content": ch, "embedding": emb}
                     for i, (ch, emb) in enumerate(zip(chunks, embeddings))]
            c.chunks.create_many(doc_id, items, c.ai.embedding_model())

            yield _sse({"type": "done", "document_id": doc_id, "alias": alias, "chunks": len(chunks)})
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})

    return Response(stream_with_context(process()), mimetype="text/event-stream")


# ── Listagem / load / delete / visibilidade ────────────────────────────
@bp.get("/pdf/indices")
@login_required
def list_indices():
    docs = _c().documents.list_visible_for(g.user_id)
    return jsonify({"indices": [{
        "document_id": d["id"], "alias": d["alias"], "filename": d["filename"],
        "visibility": d["visibility"], "is_owner": d["owner_user_id"] == g.user_id,
    } for d in docs]})


@bp.post("/pdf/load")
@login_required
def load_index():
    doc = _c().documents.get((request.get_json(silent=True) or {}).get("document_id", ""))
    if not _can_read(doc, g.user_id):
        return jsonify({"error": "Não encontrado"}), 404                   # MNG-05/CHAT-02
    return jsonify({"ok": True, "document_id": doc["id"], "alias": doc["alias"],
                    "visibility": doc["visibility"]})


@bp.post("/pdf/delete")
@login_required
def delete_index():
    c = _c()
    doc = c.documents.get((request.get_json(silent=True) or {}).get("document_id", ""))
    if not doc:
        return jsonify({"error": "Não encontrado"}), 404
    if doc["owner_user_id"] != g.user_id:
        return jsonify({"error": "Sem permissão"}), 403                    # MNG-07/08
    c.chunks.delete_by_document(doc["id"])
    c.storage.delete(doc["storage_path"])
    c.documents.delete(doc["id"])
    return jsonify({"ok": True})


@bp.patch("/pdf/<doc_id>/visibility")
@login_required
def set_visibility(doc_id):
    c = _c()
    doc = c.documents.get(doc_id)
    if not doc:
        return jsonify({"error": "Não encontrado"}), 404
    if doc["owner_user_id"] != g.user_id:
        return jsonify({"error": "Sem permissão"}), 403                    # UP-13
    vis = (request.get_json(silent=True) or {}).get("visibility")
    if vis not in ("private", "public"):
        return jsonify({"error": "Visibilidade inválida"}), 400
    c.documents.set_visibility(doc_id, vis)                                # UP-12
    return jsonify({"ok": True})


# ── Chat ───────────────────────────────────────────────────────────────
@bp.post("/chat")
@login_required
def chat():
    d = request.get_json(silent=True) or {}
    question = (d.get("question") or "").strip()
    doc_id = d.get("document_id")
    if not question:
        return jsonify({"error": "Pergunta vazia"}), 400
    if not doc_id:
        return jsonify({"error": "Nenhum report indexado. Faça o upload primeiro."}), 400  # CHAT-05
    c = _c()
    doc = c.documents.get(doc_id)
    if not _can_read(doc, g.user_id):
        return jsonify({"error": "Não encontrado"}), 404                   # CHAT-02

    rows = c.chunks.get_by_document(doc_id)
    chunks = [r["content"] for r in rows]
    embeddings = [r["embedding"] for r in rows]

    def generate():
        try:
            q_emb = c.ai.embed_query(question)
            top = rag.retrieve_top_k(q_emb, chunks, embeddings)
            system = rag.SYSTEM_PROMPT.format(alias=doc["alias"], context="\n\n---\n\n".join(top))
            for text in c.ai.stream_chat(system, question):
                yield _sse({"type": "token", "text": text})
            yield _sse({"type": "done"})
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")
