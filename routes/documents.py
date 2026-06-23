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
            pages = rag.extract_pdf_pages(data)
            text = "\n\n".join(p for p in pages if p.strip())
            if not text.strip():
                yield _sse({"type": "error", "message": "PDF sem texto extraível"})  # UP-05
                return

            yield _sse({"type": "progress", "step": "classify", "pct": 22})
            sample = " ".join(rag.chunk_text(text[:4000])[:5])[:2000]
            # Etapa 1: classificação de domínio (TI/agilidade), fail-closed.
            try:
                relevant = c.ai.is_relevant(alias, sample)
            except Exception:
                yield _sse({"type": "rejected", "message": "Não foi possível validar o documento agora. Tente novamente."})  # UP-07
                return
            if not relevant:
                yield _sse({"type": "rejected", "message": "O documento não parece ser de TI ou agilidade. Apenas reports de squads e materiais técnicos são aceitos."})  # UP-02
                return

            # Etapa 2: classificação de TIPO (só após aprovar o domínio — TYPE-07).
            # Fallback seguro: nunca interrompe o upload por falha aqui (TYPE-06).
            try:
                doc_type = c.ai.classify_type(alias, sample)
            except Exception:
                doc_type = rag.DEFAULT_DOC_TYPE

            yield _sse({"type": "progress", "step": "chunk", "pct": 38})
            if doc_type == "squad_report_multi":
                parts = rag.chunk_pages_with_squads(pages, c.ai.identify_squad)  # UC-02
            else:
                parts = [{"content": ch, "squad_name": None} for ch in rag.chunk_text(text)]
            chunks = [p["content"] for p in parts]

            yield _sse({"type": "progress", "step": "embed", "pct": 60})
            embeddings = c.ai.embed_documents(chunks)

            yield _sse({"type": "progress", "step": "store", "pct": 88})
            storage_path = f"{user_id}/{uuid.uuid4().hex}_{secure_filename(fname)}"
            c.storage.upload(storage_path, data)
            doc_id = c.documents.create(user_id, alias, secure_filename(fname),
                                        storage_path, visibility, doc_type)
            items = [{"chunk_index": i, "content": p["content"], "embedding": emb,
                      "squad_name": p["squad_name"]}
                     for i, (p, emb) in enumerate(zip(parts, embeddings))]
            c.chunks.create_many(doc_id, items, c.ai.embedding_model())

            yield _sse({"type": "done", "document_id": doc_id, "alias": alias,
                        "chunks": len(chunks), "document_type": doc_type})
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
        "visibility": d["visibility"], "document_type": d.get("document_type"),
        "is_owner": d["owner_user_id"] == g.user_id,
    } for d in docs]})


@bp.post("/pdf/load")
@login_required
def load_index():
    doc = _c().documents.get((request.get_json(silent=True) or {}).get("document_id", ""))
    if not _can_read(doc, g.user_id):
        return jsonify({"error": "Não encontrado"}), 404                   # MNG-05/CHAT-02
    return jsonify({"ok": True, "document_id": doc["id"], "alias": doc["alias"],
                    "visibility": doc["visibility"],
                    "document_type": doc.get("document_type"),
                    "is_owner": doc["owner_user_id"] == g.user_id})


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


@bp.patch("/pdf/<doc_id>/type")
@login_required
def set_doc_type(doc_id):
    # Correção manual do tipo detectado (só o dono).
    c = _c()
    doc = c.documents.get(doc_id)
    if not doc:
        return jsonify({"error": "Não encontrado"}), 404
    if doc["owner_user_id"] != g.user_id:
        return jsonify({"error": "Sem permissão"}), 403
    dt = (request.get_json(silent=True) or {}).get("document_type")
    if dt not in rag.DOC_TYPES:
        return jsonify({"error": "Tipo inválido"}), 400
    c.documents.set_type(doc_id, dt)
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
    doc_type = doc.get("document_type") or rag.DEFAULT_DOC_TYPE

    # Retrieval ciente de squad (UC-03): se a pergunta cita uma squad do documento,
    # restringe aos chunks dela + os gerais (squad_name nulo).
    if doc_type == "squad_report_multi":
        squads = {r.get("squad_name") for r in rows if r.get("squad_name")}
        mentioned = next((s for s in squads if s.lower() in question.lower()), None)
        if mentioned:
            rows = [r for r in rows if r.get("squad_name") in (mentioned, None)]
    chunks = [r["content"] for r in rows]
    embeddings = [r["embedding"] for r in rows]

    def generate():
        try:
            q_emb = c.ai.embed_query(question)
            top = rag.retrieve_top_k(q_emb, chunks, embeddings)
            system = rag.build_system_prompt(doc["alias"], doc_type, "\n\n---\n\n".join(top))
            for text in c.ai.stream_chat(system, question):
                yield _sse({"type": "token", "text": text})
            yield _sse({"type": "done"})
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")
