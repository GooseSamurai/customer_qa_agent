"""业务知识文档入库和切分。

当前使用 LangChain 的 Markdown 标题切分器，把公开业务文档切成
带来源、分类和有效期的知识片段。
"""

import json
import sys
from datetime import date
from pathlib import Path

from langchain_text_splitters import MarkdownHeaderTextSplitter
from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    """描述知识文档的来源和适用范围。"""

    source_id: str
    title: str
    source_type: str = "synthetic_sample"
    source_url: str
    channel: str
    category: str
    policy_type: str
    effective_date: date | None = None
    expire_date: date | None = None


class KnowledgeChunk(BaseModel):
    """文档切分后的一个可检索知识片段。"""

    source_id: str
    chunk_id: str
    section: str | None = None
    text: str
    metadata: DocumentMetadata


def ingest_document(
    text: str,
    metadata: DocumentMetadata,
) -> list[KnowledgeChunk]:
    """按 Markdown 标题层级切分文档。"""

    if not text.strip():
        raise ValueError("document text cannot be empty")

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "title"),
            ("##", "section"),
            ("###", "subsection"),
        ]
    )

    split_documents = splitter.split_text(text)
    chunks = []

    for index, document in enumerate(split_documents, start=1):
        section = document.metadata.get("subsection") or document.metadata.get("section")
        chunks.append(
            KnowledgeChunk(
                source_id=metadata.source_id,
                chunk_id=f"{metadata.source_id}-chunk-{index}",
                section=section,
                text=document.page_content,
                metadata=metadata,
            )
        )

    return chunks


def ingest_manifest(manifest_path: Path) -> list[KnowledgeChunk]:
    """读取 documents.json，并切分清单中的全部文档。"""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks = []

    for item in manifest:
        metadata = DocumentMetadata.model_validate(item)
        document_path = manifest_path.parent / item["file"]
        text = document_path.read_text(encoding="utf-8")
        chunks.extend(ingest_document(text, metadata))

    return chunks


def main() -> None:
    """执行 python -m rag.ingest，查看切分结果。"""

    manifest_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/knowledge/documents.json")
    chunks = ingest_manifest(manifest_path)

    for chunk in chunks:
        preview = chunk.text[:60].replace("\n", " ")
        print(f"{chunk.chunk_id} | {chunk.section} | {len(chunk.text)} | {preview}")

    print(f"total_chunks={len(chunks)}")


if __name__ == "__main__":
    main()