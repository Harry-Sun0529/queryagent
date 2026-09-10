"""Compare keyword and semantic retrieval on a fixed paraphrase set.

Reports the two separately. There is no combined "RAG accuracy" number here
on purpose: the interesting question is whether semantic retrieval earns the
external dependency it costs, and averaging the two away is how that
question stops being asked.

Recall@k denominators contain only evidence the acting subject is authorised
for and that actually applies — counting unreachable documents as misses
would make the permission model look like a quality problem.

Semantic mode needs an embeddings endpoint (QUERYAGENT_EMBEDDING_API_KEY).
Without one the script still runs and reports the keyword baseline alone,
and says so rather than presenting a baseline as a comparison.

Usage:
    python eval/run_retrieval_check.py --output eval/results/retrieval-<date>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from queryagent.knowledge.embedding import ENV_KEY, EmbeddingClient  # noqa: E402
from queryagent.knowledge.index import SqliteKnowledgeIndex  # noqa: E402
from queryagent.knowledge.provider import (  # noqa: E402
    DEFAULT_MIN_SIMILARITY,
    LocalKnowledgeProvider,
    scope_of,
)
from queryagent.workflow.models import ActorContext  # noqa: E402


@dataclass(frozen=True)
class Case:
    intent: str
    question: str
    gold: tuple[str, ...]


def load_cases(path: Path) -> tuple[str, tuple[Case, ...]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases = tuple(
        Case(intent=entry["intent"], question=question, gold=tuple(entry["gold"]))
        for entry in raw["cases"]
        for question in entry["questions"]
    )
    return raw["workspace"], cases


def recall_at_k(provider: LocalKnowledgeProvider, actor: ActorContext, cases, k: int):
    hits = 0
    misses = []
    for case in cases:
        found = provider.search(scope_of(actor), case.question, limit=k)
        sections = {" › ".join(hit.chunk.section_path) for hit in found}
        if any(gold in sections for gold in case.gold):
            hits += 1
        else:
            misses.append({"question": case.question, "intent": case.intent})
    return hits, len(cases), misses


def false_evidence(provider: LocalKnowledgeProvider, actor: ActorContext, questions, k: int):
    """Questions that retrieved *something* although the corpus has nothing.

    The other half of retrieval quality: a mode that always returns its top
    chunk scores perfectly on recall and makes "no evidence" unreachable.
    """
    flagged = []
    for question in questions:
        found = provider.search(scope_of(actor), question, limit=k)
        if found:
            flagged.append(
                {
                    "question": question,
                    "top": " › ".join(found[0].chunk.section_path),
                    "score": round(found[0].score, 3),
                }
            )
    return len(flagged), len(questions), flagged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="report directory (must not exist)")
    parser.add_argument("--cases", default="eval/knowledge/paraphrases.yaml")
    parser.add_argument("--unrelated", default="eval/knowledge/unrelated.yaml")
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=DEFAULT_MIN_SIMILARITY,
        help="semantic cosine floor (model-specific)",
    )
    parser.add_argument("--corpus", default="examples/knowledge/ops")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--embedding-base-url", default="https://api.siliconflow.cn/v1")
    args = parser.parse_args(argv)

    out = Path(args.output)
    if out.exists():
        print(f"[错误] {out} 已存在；换一个目录，不要覆盖既有证据。", file=sys.stderr)
        return 2
    out.mkdir(parents=True)

    workspace, cases = load_cases(Path(args.cases))
    actor = ActorContext(subject_id="eval", workspace_id=workspace)
    index = SqliteKnowledgeIndex(out / "index.db")
    index.import_directory(args.corpus, workspace_id=workspace)

    report: dict[str, object] = {"k": args.k, "cases": len(cases), "workspace": workspace}

    unrelated = tuple(
        yaml.safe_load(Path(args.unrelated).read_text(encoding="utf-8"))["questions"]
    )

    keyword = LocalKnowledgeProvider(index)
    hits, total, misses = recall_at_k(keyword, actor, cases, args.k)
    wrong, asked, flagged = false_evidence(keyword, actor, unrelated, args.k)
    report["keyword"] = {"recall_at_k": hits / total, "hits": hits, "total": total,
                         "misses": misses,
                         "false_evidence": {"count": wrong, "total": asked,
                                            "questions": flagged}}

    if os.environ.get(ENV_KEY):
        client = EmbeddingClient(model=args.embedding_model, base_url=args.embedding_base_url)
        index.embed_missing(workspace, client)
        semantic = LocalKnowledgeProvider(index, client, min_similarity=args.min_similarity)
        hits, total, misses = recall_at_k(semantic, actor, cases, args.k)
        wrong, asked, flagged = false_evidence(semantic, actor, unrelated, args.k)
        report["semantic"] = {"recall_at_k": hits / total, "hits": hits, "total": total,
                              "misses": misses, "model": args.embedding_model,
                              "min_similarity": args.min_similarity,
                              "false_evidence": {"count": wrong, "total": asked,
                                                 "questions": flagged}}
    else:
        report["semantic"] = {
            "measured": False,
            "reason": f"{ENV_KEY} 未设置；本次只有关键词基线，不构成对照",
        }

    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
