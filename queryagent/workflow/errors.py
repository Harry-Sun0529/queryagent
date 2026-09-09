"""Workflow errors. All refusals, deliberately distinguishable.

Every one of these is a *refusal to execute*, not a failure to try. The
distinctions matter to callers: a stale version asks the user to look again,
a permission denial must not tell them what they were denied, and a missing
mapping is a maintainer task rather than something to retry.
"""

from __future__ import annotations

from queryagent.errors import QueryAgentError


class WorkflowError(QueryAgentError):
    """Base class for trusted-workflow refusals."""


class NotFound(WorkflowError):
    """No such draft, confirmation or run."""


class PermissionDenied(WorkflowError):
    """The subject may not act on this object.

    Message text stays generic on purpose: telling a stranger *what* they
    were denied is itself a disclosure (T06).
    """


class StaleVersion(WorkflowError):
    """The caller acted on a version that is no longer current (T10, T12)."""


class ConfirmationRequired(WorkflowError):
    """Execution was attempted without a valid confirmation for this exact draft version.

    Raised for all of: never confirmed, confirmed then amended, and a
    confirmation belonging to someone else (T01, T09, T10).
    """


class WorkflowStateError(WorkflowError):
    """The requested transition is not legal from the draft's current state."""


class MappingNotFound(WorkflowError):
    """No maintainer-defined mapping covers this confirmed definition (T14).

    The deliberate alternative — letting the model guess a table — is what
    this whole layer exists to prevent.
    """
