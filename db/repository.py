"""使用 SQLite 保存质检过程数据的最小 Repository。"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db.models import AgentRunRecord, ReviewRecord
from schemas.conversation import Conversation
from schemas.evidence import ExternalEvidence
from schemas.finding import Finding


def _now() -> str:
    """返回统一格式的当前时间。"""

    return datetime.now(timezone.utc).isoformat()


class SQLiteRepository:
    """保存 case、Finding、Evidence、Agent Run 和 Review。"""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self.initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize_schema(self) -> None:
        """创建最小表结构。"""

        schema = """
        CREATE TABLE IF NOT EXISTS qa_cases (
            case_id TEXT PRIMARY KEY,
            conversation_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS qa_findings (
            finding_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            finding_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES qa_cases(case_id)
        );

        CREATE TABLE IF NOT EXISTS qa_evidence (
            evidence_id TEXT PRIMARY KEY,
            finding_id TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (finding_id) REFERENCES qa_findings(finding_id)
        );

        CREATE TABLE IF NOT EXISTS agent_runs (
            run_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            status TEXT NOT NULL,
            state_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES qa_cases(case_id)
        );

        CREATE TABLE IF NOT EXISTS qa_reviews (
            review_id TEXT PRIMARY KEY,
            finding_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            corrected_finding_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (finding_id) REFERENCES qa_findings(finding_id)
        );
        """

        with self._connect() as connection:
            connection.executescript(schema)

    def save_case(self, case_id: str, conversation: Conversation) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO qa_cases VALUES (?, ?, ?)",
                (case_id, conversation.model_dump_json(), _now()),
            )

    def get_case(self, case_id: str) -> Conversation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT conversation_json FROM qa_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        return Conversation.model_validate_json(row["conversation_json"]) if row else None

    def save_findings(self, case_id: str, findings: list[Finding]) -> list[str]:
        finding_ids = []
        with self._connect() as connection:
            for index, finding in enumerate(findings, start=1):
                finding_id = f"{case_id}-finding-{index}"
                connection.execute(
                    "INSERT OR REPLACE INTO qa_findings VALUES (?, ?, ?, ?)",
                    (finding_id, case_id, finding.model_dump_json(), _now()),
                )
                finding_ids.append(finding_id)
        return finding_ids

    def get_finding(self, finding_id: str) -> Finding | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT finding_json FROM qa_findings WHERE finding_id = ?",
                (finding_id,),
            ).fetchone()
        return Finding.model_validate_json(row["finding_json"]) if row else None

    def get_finding_record(self, finding_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT case_id, finding_json FROM qa_findings WHERE finding_id = ?",
                (finding_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "case_id": row["case_id"],
            "finding": Finding.model_validate_json(row["finding_json"]),
        }
    def save_evidence(
        self,
        finding_id: str,
        evidence: list[ExternalEvidence],
    ) -> list[str]:
        evidence_ids = []
        with self._connect() as connection:
            for index, item in enumerate(evidence, start=1):
                evidence_id = f"{finding_id}-evidence-{index}"
                connection.execute(
                    "INSERT OR REPLACE INTO qa_evidence VALUES (?, ?, ?, ?)",
                    (evidence_id, finding_id, item.model_dump_json(), _now()),
                )
                evidence_ids.append(evidence_id)
        return evidence_ids

    def save_agent_run(self, run: AgentRunRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO agent_runs VALUES (?, ?, ?, ?, ?)",
                (
                    run.run_id,
                    run.case_id,
                    run.status,
                    json.dumps(run.state, ensure_ascii=False),
                    _now(),
                ),
            )

    def get_agent_run(self, run_id: str) -> AgentRunRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM agent_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return AgentRunRecord(
            run_id=row["run_id"],
            case_id=row["case_id"],
            status=row["status"],
            state=json.loads(row["state_json"]),
        )

    def save_review(self, review: ReviewRecord) -> None:
        corrected_json = (
            review.corrected_finding.model_dump_json()
            if review.corrected_finding is not None
            else None
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO qa_reviews VALUES (?, ?, ?, ?, ?)",
                (
                    review.review_id,
                    review.finding_id,
                    review.decision.value,
                    corrected_json,
                    _now(),
                ),
            )

    def get_review(self, review_id: str) -> ReviewRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM qa_reviews WHERE review_id = ?",
                (review_id,),
            ).fetchone()
        if row is None:
            return None
        return ReviewRecord(
            review_id=row["review_id"],
            finding_id=row["finding_id"],
            decision=row["decision"],
            corrected_finding=(
                Finding.model_validate_json(row["corrected_finding_json"])
                if row["corrected_finding_json"]
                else None
            ),
        )

    def list_reviews(self) -> list[ReviewRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM qa_reviews ORDER BY created_at"
            ).fetchall()
        return [
            ReviewRecord(
                review_id=row["review_id"],
                finding_id=row["finding_id"],
                decision=row["decision"],
                corrected_finding=(
                    Finding.model_validate_json(row["corrected_finding_json"])
                    if row["corrected_finding_json"]
                    else None
                ),
            )
            for row in rows
        ]