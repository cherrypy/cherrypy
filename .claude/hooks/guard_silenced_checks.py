#! /usr/bin/env python3
"""Make Claude Code ask the operator before an agent silences or games a check.

This is a ``PreToolUse`` hook. It never blocks anything on its own: when
an edit or a shell command looks like it suppresses a linter finding,
disables or weakens a test, calls private methods from tests, or changes
tool configuration, it asks Claude Code to prompt the operator for a
decision.

See ``.agents-ctx/DONT_SHOOT_THE_MESSENGER.md`` for the policy.
"""

from __future__ import annotations

import pathlib
import re
import sys
import typing as _t

import hook_utils


POLICY_DOC = '.agents-ctx/DONT_SHOOT_THE_MESSENGER.md'

MarkerTable = _t.Iterable[tuple[str, re.Pattern[str]]]

SUPPRESSION_MARKERS = (
    ('noqa', re.compile(r'#\s*noqa\b', re.IGNORECASE)),
    ('ruff: noqa', re.compile(r'#\s*ruff\s*:\s*noqa\b')),
    ('flake8: noqa', re.compile(r'#\s*flake8\s*:\s*noqa\b')),
    ('type: ignore', re.compile(r'#\s*type\s*:\s*ignore\b')),
    ('mypy: ignore', re.compile(r'#\s*mypy\s*:\s*ignore')),
    ('pylint: disable', re.compile(r'#\s*pylint\s*:\s*disable')),
    ('pragma: no cover', re.compile(r'#\s*pragma\s*:\s*no\s*cover')),
    ('skip/skipif marker', re.compile(r'\bpytest\.mark\.skip')),
    ('xfail marker', re.compile(r'\bpytest\.mark\.xfail\b')),
    (
        'imperative skip/xfail',
        re.compile(r'\bpytest\.(?:skip|xfail|importorskip)\s*\('),
    ),
    ('continue-on-error', re.compile(r'\bcontinue-on-error\b')),
)

TEST_STRENGTH_MARKERS = (
    (
        'test functions',
        re.compile(r'^\s*(?:async\s+)?def\s+test_', re.MULTILINE),
    ),
    ('assertions', re.compile(r'^\s*assert\b', re.MULTILINE)),
    ('pytest.raises() checks', re.compile(r'\bpytest\.raises\s*\(')),
)

PRIVATE_ACCESS_MARKERS = (
    ('private method calls', re.compile(r'\._(?!_)\w+\s*\(')),
)

TOOL_CONFIG_NAMES = frozenset(
    (
        '.codecov.yml',
        '.codespellrc',
        '.coveragerc',
        '.darglint',
        '.flake8',
        '.isort.cfg',
        '.mypy.ini',
        '.pre-commit-config.yaml',
        '.pylintrc',
        '.pylintrc.toml',
        '.ruff.toml',
        '.yamllint',
        'mypy.ini',
        'nitpick-style.toml',
        'pyproject.toml',
        'pytest.ini',
        'setup.cfg',
        'tox.ini',
    ),
)

TOOL_CONFIG_DIRS = ('.claude/', '.github/workflows/')

TESTS_DIR = 'tests/'

TOOL_CONFIG_NAMES_ALTERNATION = '|'.join(
    re.escape(config_name) for config_name in sorted(TOOL_CONFIG_NAMES)
)

SHELL_BYPASS = re.compile(r'--no-verify\b|(?:^|[\s;&|])SKIP=')

SHELL_RISKY_TARGET = re.compile(
    r'\b(?:rm|mv|truncate|tee|git\s+rm|git\s+mv|sed\s+-i|perl\s+-\w*i)\b'
    r'[^|;&]*'
    rf'(?:\b{re.escape(TESTS_DIR)}|{TOOL_CONFIG_NAMES_ALTERNATION}'
    r'|\.github/workflows/|\.claude/)',
)


def _more_frequent(
    markers: MarkerTable,
    baseline: str,
    candidate: str,
) -> list[str]:
    """List the markers that occur more often in candidate than baseline.

    :param markers: Marker names and the regexes that find them.
    :param baseline: The text to compare against.
    :param candidate: The text to look for extra markers in.
    :returns: The names of the markers found more often.
    """
    return [
        marker_name
        for marker_name, marker_regex in markers
        if len(marker_regex.findall(candidate))
        > len(marker_regex.findall(baseline))
    ]


def _is_tool_config(relative_path: str) -> bool:
    """Check whether the path is a linter, test, CI or agent config.

    :param relative_path: The path relative to its checkout.
    :returns: Whether the path is a tool config.
    """
    return pathlib.PurePosixPath(relative_path).name in TOOL_CONFIG_NAMES or (
        relative_path.startswith(TOOL_CONFIG_DIRS)
    )


def _edit_concerns(
    relative_path: str,
    old_text: str,
    new_text: str,
) -> list[str]:
    """Describe why an edit tool call needs the operator's decision.

    :param relative_path: The edited path relative to its checkout.
    :param old_text: The text the edit removes.
    :param new_text: The text the edit adds.
    :returns: The concerns, if any.
    """
    concerns = [
        f'adds a suppression ({marker_name}) in {relative_path}'
        for marker_name in _more_frequent(
            SUPPRESSION_MARKERS,
            baseline=old_text,
            candidate=new_text,
        )
    ]
    if relative_path.startswith(TESTS_DIR):
        concerns.extend(
            f'reduces the number of {marker_name} in {relative_path}'
            for marker_name in _more_frequent(
                TEST_STRENGTH_MARKERS,
                baseline=new_text,
                candidate=old_text,
            )
        )
        concerns.extend(
            f'adds {marker_name} in {relative_path} '
            '(reach the code through public API instead)'
            for marker_name in _more_frequent(
                PRIVATE_ACCESS_MARKERS,
                baseline=old_text,
                candidate=new_text,
            )
        )
    if _is_tool_config(relative_path):
        concerns.append(
            f'changes tool configuration in {relative_path} '
            '(keep it in a standalone commit)',
        )
    return concerns


def _shell_concerns(command: str) -> list[str]:
    """Describe why a shell command needs the operator's decision.

    :param command: The shell command about to run.
    :returns: The concerns, if any.
    """
    concerns = [
        f'the command mentions a suppression ({marker_name})'
        for marker_name, marker_regex in SUPPRESSION_MARKERS
        if marker_regex.search(command)
    ]
    if SHELL_BYPASS.search(command):
        concerns.append('the command bypasses pre-commit hooks')
    if SHELL_RISKY_TARGET.search(command):
        concerns.append(
            'the command deletes, moves or rewrites tests or tool config',
        )
    return concerns


def _explain(concerns_summary: str) -> str:
    """Explain to the operator why their decision is needed.

    :param concerns_summary: The concerns, joined into one string.
    :returns: The prompt shown to the operator.
    """
    return (
        'Silencing or gaming checks is a decision for the operator '
        f'(see {POLICY_DOC}): {concerns_summary}. '
        'The agent must have presented this case to you first.'
    )


def main() -> int:
    """Read the hook input and ask the operator when needed.

    :returns: The process exit code.
    """
    return hook_utils.run_hook(_edit_concerns, _shell_concerns, _explain)


if __name__ == '__main__':
    sys.exit(main())
