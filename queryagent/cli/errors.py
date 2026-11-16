"""Exit codes, and turning a failure into one line of problem and one line of fix.

Exit codes are part of the 1.0 contract (ADR-006, ADR-014).
"""

from __future__ import annotations

import sys
import traceback

from queryagent.budget import (
    BudgetExceeded,
)
from queryagent.errors import AnswerError, ConnectorError, QueryAgentError, is_transient
from queryagent.workflow.errors import (
    ConfirmationRequired,
    MappingNotFound,
    PermissionDenied,
    StaleVersion,
    WorkflowError,
)

# Exit codes are part of the 1.0 contract (ADR-006, ADR-014).
EXIT_OK = 0
EXIT_USER_ERROR = 2
EXIT_EVAL_FAILED = 3  # eval ran, and some cases failed or were not measured
EXIT_INTERNAL_DEFECT = 70  # sysexits EX_SOFTWARE
EXIT_TEMPORARY_FAILURE = 75  # sysexits EX_TEMPFAIL
EXIT_INTERRUPTED = 130  # Ctrl-C, by shell convention

def _report_error(exc: BaseException, *, verbose: bool) -> int:
    """Print one line of problem, one line of fix, and classify the exit code.

    Three classes, because a script and a human need different reactions:
    the user misconfigured something (2), our code is broken (70), or the
    upstream service is having a moment (75, retryable).
    """
    if verbose:
        traceback.print_exc()
    problem, fix, code = _explain(exc)
    print(f"[错误] {problem}", file=sys.stderr)
    if fix:
        print(f"  → {fix}", file=sys.stderr)
    return code


def _is_temporary(exc: BaseException, text: str) -> bool:
    """Kept as a named seam for the CLI; the definition lives in errors."""
    return is_transient(exc)


def _workflow_fix(exc: WorkflowError) -> str:
    """Who can actually resolve this refusal."""
    if isinstance(exc, MappingNotFound):
        return (
            "这是维护者的工作：在 workflow.mappings_path 指向的映射文件里为该口径"
            "声明经过评审的 SQL。系统不会自行猜测查询。"
        )
    if isinstance(exc, StaleVersion):
        return "口径已被改动。重新查看当前版本的确认单，再确认一次。"
    if isinstance(exc, ConfirmationRequired):
        return "先确认口径再执行；未确认或已失效的口径不会执行任何查询。"
    if isinstance(exc, PermissionDenied):
        return "当前身份没有该对象的访问权限。"
    return "查看上面的说明后重试。"


def _explain(exc: BaseException) -> tuple[str, str, int]:
    """Map a failure to (what went wrong, what to do, exit code)."""
    text = str(exc)
    if isinstance(exc, ImportError):
        missing = getattr(exc, "name", "") or text
        if "clickhouse" in missing:
            return (
                "缺少 ClickHouse 可选驱动。",
                'pip install -e ".[clickhouse]"',
                EXIT_USER_ERROR,
            )
        if "pypdf" in missing:
            return (
                "缺少 PDF 可选驱动；Markdown 与 DOCX 不需要它。",
                'pip install -e ".[docs]"',
                EXIT_USER_ERROR,
            )
        return (f"缺少依赖：{missing}。", 'pip install -e ".[dev]"', EXIT_USER_ERROR)
    if isinstance(exc, FileNotFoundError):
        return (
            f"找不到文件：{exc.filename or text}。",
            "检查 --config 路径；示例配置在 examples/demo_ecommerce/ 下。",
            EXIT_USER_ERROR,
        )
    for env_var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "QUERYAGENT_EMBEDDING_API_KEY"):
        if env_var in text and "not set" in text:
            return (f"{env_var} 未设置。", f"export {env_var}=<你的 key>", EXIT_USER_ERROR)
    if isinstance(exc, BudgetExceeded):
        # E06: a full slot frees up in minutes; a spent allowance does not,
        # and telling a retry loop otherwise makes it hammer until tomorrow.
        if exc.retryable:
            return (text, "稍后重试（退出码 75 = 可重试）。", EXIT_TEMPORARY_FAILURE)
        return (
            text,
            "这是维护者在 config.yaml 的 budget 段设定的上限；只有维护者能调整，"
            "命令行参数与模型都不能提高它。",
            EXIT_USER_ERROR,
        )
    if isinstance(exc, WorkflowError):
        # A refusal from the trusted layer is the system working, not failing.
        # Each refusal has a different person who can act on it, so generic
        # "try again" advice would send every one of them to the wrong place.
        return (text, _workflow_fix(exc), EXIT_USER_ERROR)
    if isinstance(exc, ConnectorError) and "not found" in text:
        return (
            f"{text}。",
            "先运行 make demo-data 生成示例库，或修正 config 里的 database.path。",
            EXIT_USER_ERROR,
        )
    if "HTTP 401" in text or "Authentication" in text:
        # A rejected key never fixes itself; retrying is not the answer.
        return (
            "LLM 拒绝了这个 API key（401）。",
            "检查 key 是否有效、是否与 config 里的 backend/base_url 匹配。",
            EXIT_USER_ERROR,
        )
    if _is_temporary(exc, text):
        return (
            f"上游服务暂时不可用：{text[:160]}",
            "稍后重试；持续失败可在 config 里换一个 base_url 或供应商。"
            "（退出码 75 = 可重试，脚本可据此自动重跑）",
            EXIT_TEMPORARY_FAILURE,
        )
    if isinstance(exc, AnswerError):
        return (f"输入无法识别：{text}", "按提示重新输入，或直接回车取消。", EXIT_USER_ERROR)
    if isinstance(exc, ValueError):
        return (f"配置有问题：{text}", "修正 config.yaml 后重试。", EXIT_USER_ERROR)
    if isinstance(exc, QueryAgentError):
        return (text, "", EXIT_USER_ERROR)
    return (
        f"这是 QueryAgent 自身的缺陷（bug）：{type(exc).__name__}: {text}",
        "请带上 --verbose 的完整调用栈反馈；这不是你能通过改设置解决的问题。",
        EXIT_INTERNAL_DEFECT,
    )
