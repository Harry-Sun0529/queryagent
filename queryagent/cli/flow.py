"""The confirmed path's commands: ``flow``, ``mcp``, ``web``, ``drafts``, ``confirm``, ``kb``.

Each one assembles the same workflow (``workflow.wiring``) and differs only
in who the actor is and how it talks. None of them decides whether a query
runs; ``QueryWorkflow`` does.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
import uuid
from datetime import date

from queryagent.cli.errors import EXIT_USER_ERROR
from queryagent.cli.prompts import (
    _explain_missing_filter,
    _explain_missing_grouping,
    _explain_missing_period,
    _open_choices,
    _prompt_confirm,
)
from queryagent.config import load_config
from queryagent.knowledge.index import SqliteKnowledgeIndex
from queryagent.mcp.tools import make_server
from queryagent.web.server import ConfirmationServer
from queryagent.workflow.answers import (
    stated_filter,
    stated_grouping,
    stated_period,
    variant_rule,
)
from queryagent.workflow.builder import VARIANT_RULE_KEY
from queryagent.workflow.errors import (
    ConfirmationRequired,
    WorkflowStateError,
)
from queryagent.workflow.grouping import (
    GroupingError,
    find_grouping,
)
from queryagent.workflow.models import (
    FILTER_RULE_KEY,
    GROUP_RULE_KEY,
    PERIOD_RULE_KEY,
    ActorContext,
    Channel,
    DefinitionDraft,
    DraftProgress,
    DraftStatus,
)
from queryagent.workflow.render import (
    progress_label,
    render_draft,
    render_result,
)
from queryagent.workflow.service import QueryWorkflow
from queryagent.workflow.wiring import (
    WorkflowWiring,
    build_workflow,
    business_today,
    make_embedder,
)


def _cmd_kb(args: argparse.Namespace) -> int:
    """Build or inspect the document index.

    Import prints every file it took in *and* every file it could not read.
    A document missing from the index is a set of business rules silently
    absent from every future draft, and the operator is the only person in a
    position to notice (K8).
    """
    config = load_config(args.config)
    if not config.knowledge.enabled:
        raise ValueError(
            "配置里没有 knowledge.sources；文档证据未启用，flow 仍按 metrics.yaml 生成草案"
        )
    with contextlib.ExitStack() as stack:
        index = SqliteKnowledgeIndex(config.knowledge.index_path)
        stack.callback(index.close)
        if args.kb_action == "import":
            # Built before importing anything, so a missing key fails before
            # work is done rather than after half the sources are indexed.
            embedder = make_embedder(config)
            for source in config.knowledge.sources:
                print(f"[{source.workspace}] {source.path}")
                print(index.import_directory(source.path, workspace_id=source.workspace).render())
                if embedder is not None and config.knowledge.embedding is not None:
                    added = index.embed_missing(source.workspace, embedder)
                    # Said out loud: this is the moment document text leaves
                    # the machine.
                    print(
                        f"  语义向量：新增 {added} 个（正文已发送至 "
                        f"{config.knowledge.embedding.base_url}；已有向量不重复发送）"
                    )
            return 0
        workspaces = (
            [args.workspace]
            if args.workspace
            else sorted({source.workspace for source in config.knowledge.sources})
        )
        for workspace in workspaces:
            chunks = index.chunks_in(workspace)
            print(f"[{workspace}] {len(chunks)} 个片段")
            for chunk in chunks:
                print(f"  · {chunk.citation()}")
                print(f"      {chunk.text[:60]}")
        return 0


def _print_freshness(workflow: QueryWorkflow, actor: ActorContext, draft: DefinitionDraft) -> None:
    """Below the sheet, apart from it: advice about the data, not part of the 口径."""
    notes = workflow.freshness_advisory(actor, draft.draft_id)
    if notes:
        print("\n数据新鲜度（确认前的参考，不属于口径）：")
        for note in notes:
            print(f"  · {note}")

def _cmd_flow(args: argparse.Namespace) -> int:
    """Prepare a 口径, require an explicit confirmation, then execute it.

    Exit codes: 0 executed, 2 refused or declined. A decline is not an error
    in the CLI sense but it is a non-zero outcome, because a script that
    treats "the user said no" as success is a script that will eventually
    report a number nobody approved.
    """
    config = load_config(args.config)
    actor = ActorContext(subject_id=args.subject, workspace_id=args.workspace)
    today = business_today(config)
    with contextlib.ExitStack() as stack:
        wiring = build_workflow(
            config,
            actor,
            stack,
            # E14: remembered choices are offered only where a person reads
            # the sheet before anything runs.
            offer_history=not (args.yes or args.no_history),
            today=lambda: today,
        )
        for notice in wiring.notices:
            print(notice, file=sys.stderr)
        return _run_flow(wiring, actor, args, today)


def _run_flow(
    wiring: WorkflowWiring, actor: ActorContext, args: argparse.Namespace, today: date
) -> int:
    workflow = wiring.workflow
    dimensions = wiring.dimensions
    labels = wiring.labels
    request_id = uuid.uuid4().hex
    if not args.group_by:
        # Before preparing: the question alone settles this, so it should not
        # cost a model call and leave a draft nobody can use.
        try:
            find_grouping(args.question, dimensions)
        except GroupingError as exc:
            if exc.undeclared:
                print(f"[错误] {exc}", file=sys.stderr)
                return EXIT_USER_ERROR
    draft = workflow.prepare(actor, args.question, request_id=request_id)
    if args.variant:
        documented = draft.definition.rule(VARIANT_RULE_KEY)
        if documented is None or documented.value != args.variant:
            # Consume an explicit executable choice before asking about any
            # unrelated gap. The rule remains user-authored even when it
            # overrides a document or remembered choice.
            draft = workflow.amend(
                actor,
                draft.draft_id,
                expected_version=draft.version,
                rules=(variant_rule(draft.definition, args.variant, actor.authoring_source),),
            )
        # F13: a document wording adopted on the same command line that names
        # a different reading is a contradiction. The adopted rule does not
        # exist yet, so the check is against the candidate being adopted.
        for adopt_key in args.adopt:
            candidate = draft.definition.candidate(adopt_key)
            if (
                candidate is not None
                and candidate.implies
                and args.variant not in candidate.implies
            ):
                print(
                    f"[错误] 采用的文档写法对应口径 {'/'.join(candidate.implies)}，"
                    f"--variant 却选了 {args.variant}；"
                    "同一条命令里两者矛盾，请只保留一个",
                    file=sys.stderr,
                )
                return EXIT_USER_ERROR
    if args.period:
        # Stated on purpose, it replaces whatever the question's words gave.
        draft = workflow.amend(
            actor,
            draft.draft_id,
            expected_version=draft.version,
            rules=(stated_period(args.period, today, actor.authoring_source),),
        )
    if args.group_by:
        draft = workflow.amend(
            actor,
            draft.draft_id,
            expected_version=draft.version,
            rules=(stated_grouping(args.group_by, dimensions, actor.authoring_source),),
        )
    if args.value_filter:
        draft = workflow.amend(
            actor,
            draft.draft_id,
            expected_version=draft.version,
            rules=(stated_filter(args.value_filter, dimensions, actor.authoring_source),),
        )
    if PERIOD_RULE_KEY in draft.definition.missing:
        _explain_missing_period(args.question, today)
    if GROUP_RULE_KEY in draft.definition.missing:
        _explain_missing_grouping(args.question, dimensions)
    if FILTER_RULE_KEY in draft.definition.missing:
        _explain_missing_filter(args.question, dimensions, draft.definition.display_name)
    citations = wiring.citations(actor, args.question)
    print(render_draft(draft, citations, labels))
    _print_freshness(workflow, actor, draft)
    if wiring.provider is not None and not citations:
        print("\n（未检索到该身份可见的相关文档；以下口径仅来自系统映射）")

    if draft.status is DraftStatus.NEEDS_INPUT:
        rules = _open_choices(
            draft, args, citations, today, dimensions, source=actor.authoring_source
        )
        if rules is None:
            print("\n[已取消] 未选择口径，没有执行任何查询。")
            return 2
        if rules:
            draft = workflow.amend(
                actor, draft.draft_id, expected_version=draft.version, rules=rules
            )
            print()
            print(render_draft(draft, citations, labels))
            _print_freshness(workflow, actor, draft)

    if not args.yes and not _prompt_confirm():
        print("\n[已取消] 未确认口径，没有执行任何查询。")
        return 2

    confirmation = workflow.confirm(
        actor, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
    )
    run = workflow.execute(actor, confirmation.confirmation_id, idempotency_key=request_id)
    print()
    for line in render_result(draft.definition, run, labels):
        print(line)
    return 0


def _cmd_mcp(args: argparse.Namespace) -> int:
    """Serve the workflow to an agent over MCP on stdin/stdout (T44, ADR-013).

    The identity is the person who launched the server — from the host's
    configuration, never from a tool argument (P02). stdout carries
    protocol frames and nothing else; everything for a person goes to stderr.
    """
    config = load_config(args.config)
    actor = ActorContext(
        subject_id=args.subject, workspace_id=args.workspace, channel=Channel.MCP
    )
    with contextlib.ExitStack() as stack:
        wiring = build_workflow(config, actor, stack, offer_history=not args.no_history)
        for notice in wiring.notices:
            print(notice, file=sys.stderr)
        print(
            f"[mcp] 以 {actor.subject_id}@{actor.workspace_id} 的身份提供工具；"
            "Agent 能准备和执行，确认只能由人在终端或确认页完成。",
            file=sys.stderr,
        )
        return make_server(wiring, actor).serve(sys.stdin.buffer, sys.stdout.buffer)


def _cmd_web(args: argparse.Namespace) -> int:
    """Serve the local confirmation page until Ctrl-C (T45, P06).

    Bound to 127.0.0.1 only; there is no option to listen anywhere else. The
    login link is printed once and works once.
    """
    config = load_config(args.config)
    actor = ActorContext(
        subject_id=args.subject, workspace_id=args.workspace, channel=Channel.WEB
    )
    with contextlib.ExitStack() as stack:
        wiring = build_workflow(config, actor, stack, offer_history=True)
        for notice in wiring.notices:
            print(notice, file=sys.stderr)
        try:
            server = ConfirmationServer(wiring, actor, args.port)
        except OSError as exc:
            raise ValueError(
                f"无法在 127.0.0.1:{args.port} 启动确认页（{exc}）；用 --port 换一个端口"
            ) from exc
        stack.callback(server.server_close)
        print(f"确认页（{actor.subject_id}@{actor.workspace_id}）：{server.login_url}", flush=True)
        print("登录链接只能用一次，且只在本机可访问。按 Ctrl-C 关闭。", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            # 0, not 130 (ADR-006): Ctrl-C is how this command is told to end,
            # as the line above says. Nothing was interrupted part-way.
            print("\n确认页已关闭。")
    return 0


def _cmd_drafts(args: argparse.Namespace) -> int:
    """List the drafts waiting on this person, so an agent's drafts are not confirmed blind."""
    config = load_config(args.config)
    actor = ActorContext(subject_id=args.subject, workspace_id=args.workspace)
    with contextlib.ExitStack() as stack:
        # The same assembly as every other door, so "waiting" means here what
        # it means on the page. Listing asks the database nothing.
        workflow = build_workflow(config, actor, stack, offer_history=False).workflow
        waiting = [
            (draft, workflow.progress(actor, draft.draft_id))
            for draft in workflow.pending_drafts(actor)
        ]
    if not waiting:
        print(f"没有等待 {args.subject}@{args.workspace} 确认的口径。")
        return 0
    print(f"等待 {args.subject}@{args.workspace} 确认的口径：")
    for draft, progress in waiting:
        print(
            f"  #{draft.draft_id[:8]}  v{draft.version}  {progress_label(progress)}  "
            f"{draft.definition.display_name}  {draft.question}"
        )
    print("\n用 queryagent confirm <草案号> 在终端查看并确认，或用 queryagent web 在浏览器里确认。")
    return 0


def _cmd_confirm(args: argparse.Namespace) -> int:
    """Review one draft in the terminal and confirm it (T45).

    The terminal door for drafts an agent prepared over MCP: the sheet, any
    open choices as prompts, then the same y/N as ``flow``. It confirms and
    does not execute; the agent runs the confirmed version, once. Exit 0
    when confirmed (or already confirmed), 2 when declined or refused.
    """
    config = load_config(args.config)
    actor = ActorContext(subject_id=args.subject, workspace_id=args.workspace)
    today = business_today(config)
    with contextlib.ExitStack() as stack:
        wiring = build_workflow(config, actor, stack, offer_history=False, today=lambda: today)
        for notice in wiring.notices:
            print(notice, file=sys.stderr)
        workflow = wiring.workflow
        draft = workflow.find_draft(actor, args.draft_id)
        if draft.workspace_id != actor.workspace_id:
            raise WorkflowStateError(
                f"草案 #{draft.draft_id[:8]} 属于业务空间 '{draft.workspace_id}'；"
                f"加上 --workspace {draft.workspace_id} 再确认"
            )
        progress = workflow.progress(actor, draft.draft_id)
        if progress is DraftProgress.EXPIRED:
            raise ConfirmationRequired(f"draft {draft.draft_id} has expired; prepare it again")
        if progress in (DraftProgress.CONFIRMED, DraftProgress.EXECUTED):
            print(f"草案 #{draft.draft_id[:8]} v{draft.version} 的当前版本已经确认过。")
            return 0
        if progress is DraftProgress.FAILED:
            failed = workflow.last_run(actor, draft.draft_id)
            print(
                f"草案 #{draft.draft_id[:8]} v{draft.version} 上一次确认后的执行失败了"
                f"（{failed.error if failed else '原因未知'}）。那次确认已经用掉；"
                "核对后可以再确认一次。\n"
            )
        citations = wiring.citations(actor, draft.question)
        print(render_draft(draft, citations, wiring.labels))
        _print_freshness(workflow, actor, draft)
        if draft.status is DraftStatus.NEEDS_INPUT:
            asked = argparse.Namespace(
                adopt=[], rule=[], variant=None, period=None, group_by=None, value_filter=None
            )
            rules = _open_choices(
                draft, asked, citations, today, wiring.dimensions, source=actor.authoring_source
            )
            if rules is None:
                print("\n[已取消] 口径仍有未定项，没有确认。")
                return 2
            if rules:
                draft = workflow.amend(
                    actor, draft.draft_id, expected_version=draft.version, rules=rules
                )
                print()
                print(render_draft(draft, citations, wiring.labels))
                _print_freshness(workflow, actor, draft)
        if not _prompt_confirm():
            print("\n[已取消] 未确认口径，没有执行任何查询。")
            return 2
        workflow.confirm(
            actor, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
        )
        print(
            f"\n已在终端确认 #{draft.draft_id[:8]} v{draft.version}。回到 Agent，让它调用 "
            "execute_query 执行；一次确认只执行一次。"
        )
        return 0
