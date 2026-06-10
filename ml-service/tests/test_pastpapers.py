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
