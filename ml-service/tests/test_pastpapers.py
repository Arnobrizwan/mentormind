"""Pipeline tests — hermetic: stubbed OCR, temp SQLite, synthetic PDFs."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pastpapers import processor as processor_module
from app.pastpapers.models import DocumentType
from app.pastpapers.processor import align_questions, parse_filename, split_questions

QP_MARKDOWN = """# Cambridge International AS & A Level

**1** Solve the equation $2x + 3 = 11$. [2]

Show all working.

**2** A ball is thrown vertically with speed $u$.

(a) Find the maximum height. [3]

(b) State an assumption made. [1]

**3** Differentiate $y = x^2 \\sin x$ with respect to $x$. [4]
"""

MS_MARKDOWN = """# Mark Scheme

**1** $2x = 8$ M1
$x = 4$ A1

**2** (a) $h = u^2 / 2g$ M1 A1 A1
(b) Air resistance neglected B1

**3** $\\frac{dy}{dx} = 2x \\sin x + x^2 \\cos x$ M1 A1 A1 A1
"""


class TestParsing:
    def test_parse_valid_filenames(self):
        parsed = parse_filename("9709_s23_qp_12.pdf")
        assert parsed is not None
        assert parsed.subject_code == "9709"
        assert parsed.year == 2023
        assert parsed.session == "s"
        assert parsed.paper_variant == "12"
        assert parsed.document_type == DocumentType.QP

        ms = parse_filename("0580_W19_MS_42.PDF".lower())
        assert ms is not None and ms.document_type == DocumentType.MS

    def test_rejects_non_caie_names(self):
        assert parse_filename("notes.pdf") is None
        assert parse_filename("9709_qp_12.pdf") is None


class TestSplitting:
    def test_splits_numbered_questions(self):
        blocks = split_questions(QP_MARKDOWN)
        assert sorted(blocks) == [1, 2, 3]
        assert "2x + 3" in blocks[1]
        assert "maximum height" in blocks[2]
        assert "Differentiate" in blocks[3]

    def test_ignores_stray_line_numbers(self):
        text = "**1** First question with value\n20 marks total\n**2** Second"
        blocks = split_questions(text)
        # '20' at line start must not become question 20
        assert sorted(blocks) == [1, 2]

    def test_alignment_pairs_by_number(self):
        aligned = align_questions(QP_MARKDOWN, MS_MARKDOWN)
        assert [a["question_number"] for a in aligned] == [1, 2, 3]
        assert "M1" in aligned[0]["mark_scheme"]
        assert "$2x + 3 = 11$" in aligned[0]["question"]


@pytest.fixture()
def pipeline_env(tmp_path, monkeypatch):
    """Isolated DB + paper folder + stubbed OCR for endpoint tests."""
    import app.pastpapers.models as models

    db_path = tmp_path / "test.db"
    engine = models.create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    factory = models.async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "SessionFactory", factory)

    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

    asyncio.run(init())

    papers = tmp_path / "papers"
    papers.mkdir()
    (papers / "9709_s23_qp_12.pdf").write_bytes(b"%PDF-1.4 qp")
    (papers / "9709_s23_ms_12.pdf").write_bytes(b"%PDF-1.4 ms")
    (papers / "README.txt").write_text("ignore me")
    # Confine the discover path guard to this fixture's temp folder.
    monkeypatch.setenv("PASTPAPERS_ROOT", str(papers))

    async def fake_ocr(self, file_path):
        return QP_MARKDOWN if "_qp_" in file_path else MS_MARKDOWN

    monkeypatch.setattr(
        processor_module.MistralOCRService, "process_pdf_to_markdown", fake_ocr
    )
    monkeypatch.setattr(processor_module, "MARKDOWN_DIR", str(tmp_path / "md"))
    return papers


class TestPipelineEndpoints:
    def test_discover_process_dataset_flow(self, pipeline_env):
        with TestClient(app) as client:
            res = client.post("/api/pipeline/discover", json={"folder": str(pipeline_env)})
            assert res.status_code == 200
            assert res.json() == {"matched_pdfs": 2, "created": 2, "skipped_files": 0}

            # idempotent re-scan
            res = client.post("/api/pipeline/discover", json={"folder": str(pipeline_env)})
            assert res.json()["created"] == 0

            res = client.post("/api/pipeline/process-next")
            assert res.status_code == 200
            body = res.json()
            assert body["processed"] is True
            assert body["aligned_questions"] == 3

            # nothing left to process
            res = client.post("/api/pipeline/process-next")
            assert res.json()["processed"] is False

            res = client.get("/api/pipeline/dataset")
            assert res.status_code == 200
            data = res.json()
            assert data["count"] == 3
            first = data["data"][0]["messages"]
            assert [m["role"] for m in first] == ["system", "user", "assistant"]
            assert "2x + 3" in first[1]["content"]
            assert "M1" in first[2]["content"]
            assert data["data"][0]["meta"]["subject_code"] == "9709"

    def test_discover_rejects_missing_folder(self, pipeline_env):
        with TestClient(app) as client:
            res = client.post("/api/pipeline/discover", json={"folder": "/nope/missing"})
            assert res.status_code == 400


class TestTutorAnswering:
    """The custom tutor serving path: corpus retrieval, no third-party AI."""

    def _seed_corpus(self, client):
        client.post("/api/pipeline/discover", json={"folder": self.folder})
        client.post("/api/pipeline/process-next")

    def test_strong_match_returns_real_mark_scheme(self, pipeline_env):
        self.folder = str(pipeline_env)
        with TestClient(app) as client:
            self._seed_corpus(client)
            res = client.post("/v1/tutor/answer", json={
                "question": "Solve the equation 2x + 3 = 11 showing all working",
                "subject": "Math", "level": "A-Level",
            })
            assert res.status_code == 200
            body = res.json()
            assert body["matched"] is True
            assert "$x = 4$" in body["answer"]          # the actual mark scheme
            assert "mark-scheme" in body["answer"].lower()
            assert body["source"]["subject_code"] == "9709"
            assert body["source"]["question_number"] == 1

    def test_related_question_gets_method_guidance(self, pipeline_env):
        self.folder = str(pipeline_env)
        with TestClient(app) as client:
            self._seed_corpus(client)
            res = client.post("/v1/tutor/answer", json={
                "question": "A ball is thrown vertically upward, how high does it go?",
            })
            body = res.json()
            assert res.status_code == 200
            # grounded in the nearest real mark scheme either way
            assert "u^2 / 2g" in body["answer"]
            assert body["source"]["question_number"] == 2

    def test_unknown_question_admits_gap(self, pipeline_env):
        self.folder = str(pipeline_env)
        with TestClient(app) as client:
            self._seed_corpus(client)
            res = client.post("/v1/tutor/answer", json={
                "question": "Describe the economic causes of the French Revolution",
            })
            body = res.json()
            assert body["matched"] is False
            assert body["source"] is None
            assert "corpus" in body["answer"]

    def test_empty_question_rejected(self, pipeline_env):
        self.folder = str(pipeline_env)
        with TestClient(app) as client:
            res = client.post("/v1/tutor/answer", json={"question": "  "})
            assert res.status_code == 400


class TestPrecomputedEmbeddings:
    """Whole-corpus semantic index built from embeddings persisted on rows."""

    def test_index_path_serves_strong_match(self, pipeline_env):
        import numpy as np
        from sqlalchemy import select

        import app.pastpapers.models as models
        from app.pastpapers import answering
        from app.pastpapers.models import AlignedQuestion

        model = answering.get_embedding_model()
        if model is None:
            pytest.skip("sentence-transformers unavailable")

        with TestClient(app) as client:
            client.post("/api/pipeline/discover", json={"folder": str(pipeline_env)})
            client.post("/api/pipeline/process-next")

            async def embed_all():
                async with models.SessionFactory() as session:
                    rows = (await session.execute(select(AlignedQuestion))).scalars().all()
                    for row in rows:
                        vec = model.encode(
                            row.question_markdown, convert_to_numpy=True
                        ).astype(np.float32)
                        row.embedding = (vec / np.linalg.norm(vec)).tobytes()
                    await session.commit()
                    return len(rows)

            embedded = asyncio.run(embed_all())
            assert embedded == 3

            res = client.post("/v1/tutor/answer", json={
                "question": "Solve the equation 2x + 3 = 11 showing all working",
            })
            assert res.status_code == 200
            body = res.json()
            assert body["matched"] is True
            assert "$x = 4$" in body["answer"]
            # the answer came from the precomputed index, not request-time encoding
            assert answering._index_matrix is not None
            assert len(answering._index_ids) == 3
            assert not answering._vector_cache


class TestFrontMatterHandling:
    def test_cover_page_numbers_are_skipped(self):
        doc = """Cambridge International AS & A Level
1 hour 50 minutes
INSTRUCTIONS: Answer all questions.

1 Unless a particular method is specified, full marks for any method.

---

1 Solve $x^2 = 9$. [2]

2 Factorise $x^2 - 4$. [2]

3 Integrate $3x^2$. [2]
"""
        blocks = split_questions(doc)
        assert sorted(blocks) == [1, 2, 3]
        assert "Solve" in blocks[1]          # the real Q1, not the cover lines
        assert "hour" not in blocks[1]
        assert "Unless a particular" not in blocks[1]


class TestOfflineInference:
    def test_local_llm_disabled_returns_none(self, monkeypatch):
        from app.pastpapers import local_llm

        monkeypatch.delenv("LOCAL_LLM", raising=False)
        assert local_llm.is_enabled() is False
        assert local_llm.generate("2+2?", "You are a tutor.") is None

    def test_answering_is_fully_local_without_model(self, pipeline_env):
        """With no LOCAL_LLM and no CUSTOM_LLM_URL, answers still come —
        from the corpus — so the tutor works with zero network."""
        import os
        from app.pastpapers import answering

        os.environ.pop("CUSTOM_LLM_URL", None)
        os.environ.pop("LOCAL_LLM", None)

        with TestClient(app) as client:
            client.post("/api/pipeline/discover", json={"folder": str(pipeline_env)})
            client.post("/api/pipeline/process-next")
            res = client.post("/v1/tutor/answer", json={
                "question": "Solve the equation 2x + 3 = 11",
            })
            assert res.status_code == 200
            assert res.json()["matched"] is True
            assert "$x = 4$" in res.json()["answer"]

    def test_system_prompt_is_context_aware(self):
        from app.pastpapers import answering

        grounded = answering._system_prompt("Physics", "A-Level", "Q: ...\nMS: ...")
        general = answering._system_prompt("Physics", "A-Level", "")
        # Grounded mode keeps the mark-scheme instruction + embeds material.
        assert "mark-scheme" in grounded
        assert "reference material" in grounded.lower()
        # General mode answers from the model's own knowledge, no phantom
        # "reference material" with nothing after it.
        assert "from your own knowledge" in general
        assert "reference material" not in general.lower()

    def test_chat_completions_endpoint_resolution(self):
        from app.pastpapers import answering

        f = answering._chat_completions_endpoint
        assert f("http://localhost:8000") == "http://localhost:8000/v1/chat/completions"
        assert f("http://localhost:11434/v1") == "http://localhost:11434/v1/chat/completions"
        assert f("https://api.groq.com/openai/v1") == "https://api.groq.com/openai/v1/chat/completions"
        assert (
            f("https://generativelanguage.googleapis.com/v1beta/openai")
            == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        )
        # An explicit endpoint is left untouched.
        assert f("http://h/v1/chat/completions/") == "http://h/v1/chat/completions"

    def test_unknown_question_uses_model_when_available(self, pipeline_env, monkeypatch):
        """With a model configured (e.g. Gemma via LOCAL_LLM), a question with
        no corpus match is answered by the model instead of admitting a gap."""
        from app.pastpapers import answering

        captured = {}

        async def fake_generate(question, subject, level, context, history=None):
            captured["context"] = context
            return "A general tutor answer."

        monkeypatch.setattr(answering, "_generate_answer", fake_generate)

        with TestClient(app) as client:
            client.post("/api/pipeline/discover", json={"folder": str(pipeline_env)})
            client.post("/api/pipeline/process-next")
            res = client.post("/v1/tutor/answer", json={
                "question": "Who painted the Mona Lisa?",
            })
            body = res.json()
            assert body["matched"] is False
            assert body["answer"] == "A general tutor answer."
            # No corpus match -> the model was asked with empty grounding.
            assert captured["context"] == ""
