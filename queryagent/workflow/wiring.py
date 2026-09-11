"""Assembling the trusted workflow from a config: one wiring for every door (P01).

The terminal, the confirmation page and the MCP server need the same
workflow: the same store, budget, builders and compiler. A difference
between their assemblies would be a difference in what each lets through,
so they are assembled here, once. Each door differs only in who the actor
is and how it talks.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone, tzinfo
from zoneinfo import ZoneInfo

from queryagent.budget import Budget, SqliteBudgetLedger, Unmetered
from queryagent.config import AppConfig
from queryagent.connectors import make_connector
from queryagent.connectors.base import Connector
from queryagent.knowledge.embedding import EmbeddingClient
from queryagent.knowledge.index import SqliteKnowledgeIndex
from queryagent.knowledge.provider import LocalKnowledgeProvider, scope_of
from queryagent.llm import make_backend
from queryagent.metrics.yaml_store import YamlMetricStore
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import TemplateCompiler
from queryagent.workflow.enforcement import enforcement_table
from queryagent.workflow.evidence_builder import CompositeDraftBuilder, EvidenceDraftBuilder
from queryagent.workflow.execution import make_connector_executor
from queryagent.workflow.freshness import PROBE, FreshnessPolicy
from queryagent.workflow.grouping import Dimension
from queryagent.workflow.history import HistoryDraftBuilder
from queryagent.workflow.mappings import load_dimensions, load_mappings
from queryagent.workflow.models import ActorContext, DefinitionDraft
from queryagent.workflow.render import render_draft
from queryagent.workflow.service import DraftBuilder, QueryWorkflow
from queryagent.workflow.store import SqliteWorkflowStore


@dataclass(frozen=True)
class WorkflowWiring:
    """The assembled workflow, and what a door needs to talk about its drafts."""

    workflow: QueryWorkflow
    metrics: YamlMetricStore
    dimensions: tuple[Dimension, ...]
    provider: LocalKnowledgeProvider | None
    today: Callable[[], date]
    notices: tuple[str, ...]
    """Things the operator should hear before the first draft, for stderr."""
    zone: tzinfo = timezone.utc
    """The business time zone: what a page shows a stored moment in."""

    @property
    def labels(self) -> dict[str, str]:
        """Dimension keys to the maintainer's names for them."""
        return {dimension.key: dimension.label for dimension in self.dimensions}

    def citations(self, actor: ActorContext, question: str) -> dict[str, str]:
        """Human-readable locations for whatever this identity can actually see.

        Retrieval is scoped, so a document in another workspace simply is not
        in the result: there is nothing to redact afterwards.
        """
        if self.provider is None:
            return {}
        hits = self.provider.search(scope_of(actor), question, limit=8)
        return {f"{hit.ref.doc_id}#{hit.ref.chunk_id}": hit.chunk.citation() for hit in hits}

    def sheet(self, actor: ActorContext, draft: DefinitionDraft) -> str:
        """The confirmation sheet as the terminal prints it."""
        return render_draft(draft, self.citations(actor, draft.question), self.labels)


def business_today(config: AppConfig) -> date:
    """Today in the configured business time zone: what 「上个月」 is relative to."""
    return datetime.now(ZoneInfo(config.workflow.timezone)).date()


def build_workflow(
    config: AppConfig,
    actor: ActorContext,
    stack: contextlib.ExitStack,
    *,
    offer_history: bool,
    today: Callable[[], date] | None = None,
) -> WorkflowWiring:
    """Open everything the workflow needs, registering each release on ``stack``.

    Args:
        config: The loaded configuration. The workflow needs declared
            metrics and a maintainer mapping file; without either there is
            nothing it may run, and that is said before anything opens.
        actor: Who this door acts for. Used here only to say, up front,
            when the actor's workspace has no documents.
        stack: Releases the connector, the stores and the budget ledger.
        offer_history: Whether remembered choices are proposed (T42). Only
            where a person reads the sheet before anything runs (E14).
        today: Which day relative time words resolve against. A long-running
            door leaves it to follow the clock; one command fixes it.
    """
    if not config.metrics_path:
        raise ValueError(
            "flow needs declared business metrics; set metrics_path in the config file"
        )
    if not config.workflow.mappings_path:
        raise ValueError(
            "flow needs a maintainer mapping file; set workflow.mappings_path in the config "
            "file (see examples/query_mappings.yaml)"
        )
    resolve_today = today or (lambda: business_today(config))
    dimensions = load_dimensions(config.workflow.mappings_path)
    mappings = load_mappings(config.workflow.mappings_path)
    metrics = YamlMetricStore(config.metrics_path)
    notices: list[str] = []

    connector = make_connector(config.database, max_rows_scanned=scan_limit(config))
    stack.callback(connector.close)
    store = SqliteWorkflowStore(config.workflow.state_path)
    stack.callback(store.close)
    provider = None
    evidence = None
    if config.knowledge.enabled:
        index = SqliteKnowledgeIndex(config.knowledge.index_path)
        stack.callback(index.close)
        provider = knowledge_provider(index, config)
        if provider.is_semantic and not index.vectors_in(actor.workspace_id):
            # K10: the provider falls back to keyword on an un-embedded
            # corpus. Legitimate — but not silently.
            notices.append(
                "[提示] 已配置语义检索，但该业务空间尚无向量；本次按关键词检索。"
                "运行 queryagent kb import 生成向量。"
            )
        evidence = EvidenceDraftBuilder(
            provider,
            make_backend(config.llm),
            required_keys=(),  # gaps come from the maintainer metric, not extraction
        )
    compiler = TemplateCompiler(mappings, dialect=connector.dialect, dimensions=dimensions)
    builder: DraftBuilder = CompositeDraftBuilder(
        MetricDraftBuilder(metrics, today=resolve_today, dimensions=dimensions),
        evidence,
        enforcement=enforcement_table(mappings),
    )
    if offer_history:
        builder = HistoryDraftBuilder(
            builder,
            store,
            fingerprint=compiler.fingerprint,
            ref_checker=provider,
            zone=ZoneInfo(config.workflow.timezone),
            max_age_days=config.workflow.history_max_age_days,
        )
    workflow = QueryWorkflow(
        store=store,
        builder=builder,
        compiler=compiler,
        executor=make_connector_executor(
            connector,
            timeout_s=config.safety.timeout_s,
            max_rows=config.safety.max_rows,
        ),
        ref_checker=provider,
        budget=make_budget(config, stack),
        freshness=freshness_policy(config, connector, resolve_today),
    )
    known = {source.workspace for source in config.knowledge.sources}
    if provider is not None and actor.workspace_id not in known:
        # Retrieving nothing because the workspace does not exist looks
        # exactly like the documents being silent, and the second is a
        # claim about the business. Say which it is.
        notices.append(
            f"[提示] 业务空间 '{actor.workspace_id}' 没有配置任何文档来源"
            f"（已配置：{', '.join(sorted(known))}）；本次不会有文档依据。"
        )
    return WorkflowWiring(
        workflow=workflow,
        metrics=metrics,
        dimensions=dimensions,
        provider=provider,
        today=resolve_today,
        notices=tuple(notices),
        zone=ZoneInfo(config.workflow.timezone),
    )


def make_budget(config: AppConfig, stack: contextlib.ExitStack) -> Budget:
    """The maintainer's totals, or none when ``budget:`` is absent (slice 1E).

    Kept in the workflow state file, so every process pointed at it — two
    terminals, a script beside a chat, an MCP server beside them — shares one
    count.
    """
    if config.budget is None:
        return Unmetered()
    ledger = SqliteBudgetLedger(
        config.workflow.state_path,
        config.budget,
        statement_timeout_s=config.safety.timeout_s,
        zone=ZoneInfo(config.workflow.timezone),
    )
    stack.callback(ledger.close)
    return ledger


def freshness_policy(
    config: AppConfig, connector: Connector, today: Callable[[], date]
) -> FreshnessPolicy:
    """ADR-010: the declared cadence by default; the probe only if the maintainer opted in."""
    workflow = config.workflow
    probe = (
        make_connector_executor(
            connector, timeout_s=workflow.freshness_probe_timeout_s, max_rows=1
        )
        if workflow.freshness_before_confirm == PROBE
        else None
    )
    return FreshnessPolicy(
        mode=workflow.freshness_before_confirm,
        today=today,
        probe=probe,
        cache_minutes=workflow.freshness_cache_minutes,
        zone=ZoneInfo(workflow.timezone),
    )


def make_embedder(config: AppConfig) -> EmbeddingClient | None:
    embedding = config.knowledge.embedding
    if embedding is None:
        return None
    return EmbeddingClient(model=embedding.model, base_url=embedding.base_url)


def knowledge_provider(index: SqliteKnowledgeIndex, config: AppConfig) -> LocalKnowledgeProvider:
    """Keyword unless ``knowledge.embedding`` is configured."""
    embedder = make_embedder(config)
    embedding = config.knowledge.embedding
    if embedder is None or embedding is None or embedding.min_similarity is None:
        return LocalKnowledgeProvider(index, embedder)
    return LocalKnowledgeProvider(index, embedder, min_similarity=embedding.min_similarity)


def scan_limit(config: AppConfig) -> int | None:
    return config.budget.max_rows_scanned if config.budget else None
