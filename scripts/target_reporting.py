"""Formatting helpers for target assessment progress reporting."""

if __package__:
    from .target_awareness import TargetAssessment, TargetIdentity
    from .tools import ForegroundWindowSnapshot
else:
    from target_awareness import TargetAssessment, TargetIdentity
    from tools import ForegroundWindowSnapshot


def _format_identity(identity: TargetIdentity | None) -> str:
    if identity is None:
        return "unknown"

    details = []
    if identity.title:
        details.append(f"title={identity.title!r}")
    if identity.window_handle is not None:
        details.append(f"handle=0x{identity.window_handle:X}")
    if identity.process_id is not None:
        details.append(f"process id={identity.process_id}")
    return ", ".join(details) if details else "identity unavailable"


def _format_foreground(snapshot: ForegroundWindowSnapshot | None) -> str:
    if snapshot is None:
        return "unavailable"
    if snapshot.error:
        return f"observation error: {snapshot.error}"

    identity = TargetIdentity(
        window_handle=snapshot.window_handle,
        process_id=snapshot.process_id,
        title=snapshot.title,
    )
    if not any((
        identity.window_handle is not None,
        identity.process_id is not None,
        identity.title is not None,
    )):
        return "none"
    return _format_identity(identity)


def format_target_assessment(
    assessment: TargetAssessment,
    foreground: ForegroundWindowSnapshot | None,
    dispatch_blocked: bool = False,
    error: str | None = None,
) -> list[str]:
    """Format target evidence and any dispatch block for GUI progress output."""
    lines = [
        (
            "Target assessment: "
            f"{assessment.status.value.replace('_', ' ')} "
            f"({assessment.confidence.value} confidence)"
        ),
        f"Expected target: {_format_identity(assessment.expected)}",
        f"Observed foreground: {_format_foreground(foreground)}",
        f"Assessment detail: {assessment.reason}",
    ]
    if dispatch_blocked:
        explanation = error or assessment.reason
        lines.append(f"Dispatch blocked: {explanation}")
    return lines
