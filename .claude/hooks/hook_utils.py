"""Helpers shared by the Claude Code ``PreToolUse`` hooks in this directory."""

from __future__ import annotations

import contextlib
import json
import os
import pathlib
import sys
import typing as _t


EditConcerns = _t.Callable[[str, str, str], list[str]]
ShellConcerns = _t.Callable[[str], list[str]]
Explanation = _t.Callable[[str], str]


def relative_path(file_path: str, project_dir: pathlib.Path) -> str:
    """Return ``file_path`` relative to its checkout, POSIX-style.

    Files outside the project directory, e.g. in another worktree of
    the same repository, are resolved against their own worktree.

    :param file_path: The path an edit tool call targets.
    :param project_dir: The checkout Claude Code runs in.
    :returns: The POSIX-style path relative to its checkout, or the
              absolute one if it is outside of any.
    """
    absolute_path = pathlib.Path(file_path)
    if not absolute_path.is_absolute():
        absolute_path = project_dir / absolute_path
    absolute_path = absolute_path.resolve()
    worktree_dir = next(
        (
            candidate_dir
            for candidate_dir in absolute_path.parents
            if (candidate_dir / '.git').exists()
        ),
        project_dir,
    )
    for checkout_dir in (project_dir, worktree_dir):
        with contextlib.suppress(ValueError):
            return absolute_path.relative_to(checkout_dir).as_posix()
    return absolute_path.as_posix()


def edit_texts(
    tool_name: str,
    tool_input: _t.Mapping[str, _t.Any],
    project_dir: pathlib.Path,
) -> tuple[str, str]:
    """Collect the text an edit tool removes and the text it adds.

    :param tool_name: The name of the edit tool.
    :param tool_input: The arguments of the edit tool call.
    :param project_dir: The checkout relative paths are resolved
                        against.
    :returns: The removed and the added text.
    """
    if tool_name == 'Write':
        target_path = pathlib.Path(tool_input.get('file_path', ''))
        if not target_path.is_absolute():
            target_path = project_dir / target_path
        try:
            old_text = target_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            old_text = ''
        return old_text, tool_input.get('content', '')

    if tool_name == 'NotebookEdit':
        return '', tool_input.get('new_source', '')

    edits = tool_input.get('edits') or (tool_input,)
    return (
        '\n'.join(edit.get('old_string', '') for edit in edits),
        '\n'.join(edit.get('new_string', '') for edit in edits),
    )


def ask_operator(decision_reason: str) -> None:
    """Tell Claude Code to prompt the operator, giving the reason.

    :param decision_reason: The explanation shown to the operator.
    """
    json.dump(
        {
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': 'ask',
                'permissionDecisionReason': decision_reason,
            },
        },
        sys.stdout,
    )


def edit_context(
    hook_input: _t.Mapping[str, _t.Any],
    project_dir: pathlib.Path,
) -> tuple[str, str, str]:
    """Resolve an edit tool call to its path, old text and new text.

    :param hook_input: The ``PreToolUse`` hook input.
    :param project_dir: The checkout Claude Code runs in.
    :returns: The edited path relative to its checkout, the removed
              text and the added text.
    """
    tool_input = hook_input.get('tool_input', {})
    edited_path = relative_path(
        tool_input.get('file_path') or tool_input.get('notebook_path', ''),
        project_dir,
    )
    old_text, new_text = edit_texts(
        hook_input.get('tool_name', ''),
        tool_input,
        project_dir,
    )
    return edited_path, old_text, new_text


def run_hook(
    edit_concerns: EditConcerns,
    shell_concerns: ShellConcerns,
    explain: Explanation,
) -> int:
    """Read the hook input and ask the operator when needed.

    :param edit_concerns: Describes the concerns about an edit.
    :param shell_concerns: Describes the concerns about a shell
                           command.
    :param explain: Turns the concerns into the operator prompt.
    :returns: The process exit code.
    """
    hook_input = json.load(sys.stdin)
    project_dir = pathlib.Path(
        os.environ.get('CLAUDE_PROJECT_DIR') or hook_input.get('cwd', '.'),
    ).resolve()

    if hook_input.get('tool_name') == 'Bash':
        concerns = shell_concerns(
            hook_input.get('tool_input', {}).get('command', ''),
        )
    else:
        concerns = edit_concerns(*edit_context(hook_input, project_dir))

    if concerns:
        ask_operator(explain('; '.join(concerns)))
    return 0
