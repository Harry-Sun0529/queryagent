"""HTML for the confirmation page. Every string that reaches it is escaped (H7).

The sheet is the terminal's sheet, line for line (``render.sheet_lines``), so
the page cannot show a different 口径 from the one the terminal would. What
the page adds is highlighting the lines an agent filled in, and two forms.

Nothing here writes a ``<script>``, and the server's Content-Security-Policy
refuses to run one. Escaping is still done everywhere: document quotes,
questions and an agent's values are untrusted text, and the policy is the
second wall, not the first.
"""

from __future__ import annotations

import html
from collections.abc import Callable, Sequence
from datetime import datetime, tzinfo

from queryagent.workflow.answers import open_gaps
from queryagent.workflow.models import (
    VARIANT_RULE_KEY,
    Confirmation,
    DefinitionDraft,
    DraftProgress,
)
from queryagent.workflow.render import SheetLine, rule_label

FormToken = Callable[[str], str]
"""The form token for an action on the draft shown: ``amend`` or ``confirm``."""

PROGRESS_LABELS = {
    DraftProgress.NEEDS_INPUT: "待补充",
    DraftProgress.AWAITING_CONFIRMATION: "待确认",
    DraftProgress.CONFIRMED: "已确认，等待执行",
    DraftProgress.EXECUTED: "已执行",
    DraftProgress.EXPIRED: "已失效",
}

CHANNEL_LABELS = {"cli": "终端", "web": "确认页"}

_CSS = """
body{font:15px/1.65 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
  max-width:920px;margin:2rem auto;padding:0 1rem;color:#1f2328;background:#fff}
h1{font-size:1.35rem;margin:.2rem 0 1rem}
a{color:#0969da}
pre.sheet,pre.result{background:#f6f8fa;border:1px solid #d0d7de;border-radius:6px;
  padding:1rem;overflow-x:auto;white-space:pre-wrap;word-break:break-word}
mark.agent{background:#fff1b8;border-left:3px solid #d4a72c;padding:0 .25rem}
.status{display:inline-block;padding:.1rem .6rem;border-radius:1rem;background:#ddf4ff}
.note{color:#57606a}
.warn{background:#fff8c5;border:1px solid #d4a72c;border-radius:6px;padding:.6rem .9rem}
.error{background:#ffebe9;border:1px solid #ff8182;border-radius:6px;padding:.6rem .9rem}
form{margin:1.2rem 0;padding:1rem;border:1px solid #d0d7de;border-radius:6px}
label{display:block;margin:.5rem 0 .2rem;font-weight:600}
input[type=text],select{width:100%;max-width:560px;padding:.35rem;font:inherit}
button{display:block;margin-top:.9rem;padding:.45rem 1.2rem;font:inherit;border-radius:6px;
  border:1px solid #1f883d;background:#1f883d;color:#fff;cursor:pointer}
table{border-collapse:collapse;width:100%}
td,th{border-bottom:1px solid #d0d7de;padding:.45rem;text-align:left;vertical-align:top}
"""


def esc(value: object) -> str:
    """Escape for both element text and attribute values."""
    return html.escape(str(value), quote=True)


def layout(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)} · QueryAgent</title><style>{_CSS}</style></head>"
        f"<body>{body}</body></html>"
    )


def message_page(title: str, text: str, *, back: str = "/") -> str:
    back_link = f'<p><a href="{esc(back)}">返回</a></p>' if back else ""
    return layout(title, f"<h1>{esc(title)}</h1><p class=\"error\">{esc(text)}</p>{back_link}")


def pending_page(
    subject: str, workspace: str, drafts: Sequence[DefinitionDraft], zone: tzinfo
) -> str:
    rows = "".join(
        "<tr>"
        f'<td><a href="/drafts/{esc(d.draft_id)}">#{esc(d.draft_id[:8])}</a></td>'
        f"<td>v{d.version}</td>"
        f"<td>{esc(d.question)}</td>"
        f"<td>{esc(d.definition.display_name)}</td>"
        f"<td>{esc(_when(d.updated_at, zone))}</td>"
        "</tr>"
        for d in drafts
    )
    table = (
        "<table><tr><th>草案</th><th>版本</th><th>问题</th><th>指标</th><th>更新</th></tr>"
        f"{rows}</table>"
        if drafts
        else '<p class="note">没有等待你确认的口径。Agent 调用 prepare_query 后，'
        "草案会出现在这里。</p>"
    )
    return layout(
        "待确认的口径",
        f"<h1>待确认的口径</h1><p class=\"note\">{esc(subject)} @ {esc(workspace)}</p>{table}",
    )


def draft_page(
    draft: DefinitionDraft,
    sheet: Sequence[SheetLine],
    *,
    progress: DraftProgress,
    freshness: Sequence[str],
    confirmation: Confirmation | None,
    result: Sequence[str],
    token: FormToken,
    zone: tzinfo,
) -> str:
    parts = [
        '<p><a href="/">← 待确认列表</a></p>',
        f"<h1>口径确认 #{esc(draft.draft_id[:8])} · v{draft.version}</h1>",
        f'<p><span class="status">{esc(PROGRESS_LABELS[progress])}</span></p>',
        _sheet(sheet),
    ]
    if any(line.agent for line in sheet):
        parts.append(
            '<p class="warn">黄色标记的规则是 Agent 替你填的：取值可能出自文档，但这个选择是 '
            "Agent 做的，不是你。请逐条核对；确认即表示你认可它们。</p>"
        )
    if freshness:
        items = "".join(f"<li>{esc(note)}</li>" for note in freshness)
        parts.append(f"<p>数据新鲜度（确认前的参考，不属于口径）：</p><ul>{items}</ul>")
    if confirmation is not None:
        channel = CHANNEL_LABELS.get(confirmation.channel.value, confirmation.channel.value)
        parts.append(
            f'<p class="note">你已于 {esc(_when(confirmation.confirmed_at, zone))} 在{esc(channel)}'
            "确认当前版本。Agent 调用 execute_query 即可执行，一次确认只执行一次。</p>"
        )
    if result:
        parts.append(f'<pre class="result">{esc(chr(10).join(result))}</pre>')
    if progress is DraftProgress.AWAITING_CONFIRMATION:
        parts.append(_confirm_form(draft, token("confirm")))
    if progress in (DraftProgress.NEEDS_INPUT, DraftProgress.AWAITING_CONFIRMATION):
        parts.append(_amend_form(draft, token("amend")))
    if progress is DraftProgress.EXPIRED:
        parts.append('<p class="error">口径所依据的文档已失效；请让 Agent 重新生成确认单。</p>')
    return layout(f"口径确认 #{draft.draft_id[:8]}", "".join(parts))


def _sheet(lines: Sequence[SheetLine]) -> str:
    rendered = [
        f'<mark class="agent">{esc(line.text)}</mark>' if line.agent else esc(line.text)
        for line in lines
    ]
    return '<pre class="sheet">' + "\n".join(rendered) + "</pre>"


def _hidden(draft: DefinitionDraft, token: str) -> str:
    return (
        f'<input type="hidden" name="version" value="{draft.version}">'
        f'<input type="hidden" name="hash" value="{esc(draft.definition_hash)}">'
        f'<input type="hidden" name="token" value="{esc(token)}">'
    )


def _confirm_form(draft: DefinitionDraft, token: str) -> str:
    return (
        f'<form method="post" action="/drafts/{esc(draft.draft_id)}/confirm">'
        f"{_hidden(draft, token)}"
        f"<p>确认的是上面这一版（v{draft.version}，内容指纹 {esc(draft.definition_hash[:16])}）。"
        "期间若有人改动口径，这次确认会被拒绝。</p>"
        "<button type=\"submit\">确认按以上口径执行</button></form>"
    )


def _amend_form(draft: DefinitionDraft, token: str) -> str:
    definition = draft.definition
    missing = set(definition.missing)
    fields = []
    variants = [c for c in definition.candidates if c.rule_key == VARIANT_RULE_KEY]
    if variants:
        readings = "".join(
            f'<option value="{esc(c.key)}">{esc(c.label)} — {esc(c.summary)}</option>'
            for c in variants
        )
        fields.append(
            _label("选定口径", VARIANT_RULE_KEY in missing)
            + f'<select name="variant"><option value="">（不改）</option>{readings}</select>'
        )
    disputes: dict[str, list[str]] = {}
    for c in definition.candidates:
        if c.rule_key != VARIANT_RULE_KEY:
            disputes.setdefault(c.rule_key, []).append(
                f'<option value="{esc(c.key)}">{esc(c.label)}：{esc(c.summary)}</option>'
            )
    for rule_key, options in disputes.items():
        fields.append(
            _label(f"文档分歧 · {rule_label(rule_key)}", rule_key in missing)
            + f'<select name="adopt:{esc(rule_key)}"><option value="">（不采用）</option>'
            + "".join(options)
            + "</select>"
        )
    for name, key, hint in (
        ("period", "period", "如 上个月、2026-08-01..2026-08-31"),
        ("group_by", "group_by", "day / week / month / 维度名；一个总数写 none"),
        ("filter", "filter", "如 渠道=广告；不过滤写 none"),
    ):
        fields.append(
            _label(rule_label(key), key in missing)
            + f'<input type="text" name="{name}" placeholder="{esc(hint)}">'
        )
    for key in open_gaps(definition):
        fields.append(
            _label(rule_label(key), True)
            + f'<input type="text" name="rule:{esc(key)}" placeholder="写下本次约定">'
        )
    return (
        f'<form method="post" action="/drafts/{esc(draft.draft_id)}/amend">'
        f"{_hidden(draft, token)}<p><strong>补充或修改口径</strong>"
        '<span class="note">（留空的项不改；提交后产生新版本，需要重新确认）</span></p>'
        + "".join(fields)
        + '<button type="submit">提交补充</button></form>'
    )


def _label(text: str, open_item: bool) -> str:
    return f"<label>{esc(text)}{'（待定）' if open_item else ''}</label>"


def _when(moment: datetime, zone: tzinfo) -> str:
    """A stored moment (UTC) in the business time zone the reader lives in."""
    return moment.astimezone(zone).strftime("%Y-%m-%d %H:%M")
