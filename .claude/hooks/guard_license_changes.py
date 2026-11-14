#! /usr/bin/env python3
"""Make Claude Code ask the operator before an agent touches licensing.

This is a ``PreToolUse`` hook. It never blocks anything on its own: when
an edit or a shell command looks like it changes a license file or drops
license notices, it asks Claude Code to prompt the operator for a
decision.

See ``.agents-ctx/LICENSING.md`` for the policy.
"""

from __future__ import annotations

import pathlib
import re
import sys

import hook_utils


POLICY_DOC = '.agents-ctx/LICENSING.md'

LICENSE_FILE_NAME = re.compile(
    r'^(?:LICEN[CS]E|COPYING|NOTICE)(?:[.-].*)?$',
    re.IGNORECASE,
)

LICENSE_NOTICE = re.compile(
    r'\bLicen[cs]e\b|SPDX-License-Identifier',
    re.IGNORECASE,
)

LICENSE_METADATA = re.compile(
    r'^\s*license(?:[-_]files?)?\s*[=:].*$',
    re.IGNORECASE | re.MULTILINE,
)

SHELL_LICENSE_TARGET = re.compile(
    r'\b(?:rm|mv|truncate|tee|git\s+rm|git\s+mv|sed\s+-i|perl\s+-\w*i)\b'
    r'[^|;&]*'
    r'\b(?:LICEN[CS]E|COPYING|NOTICE)',
    re.IGNORECASE,
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
    concerns = []
    if LICENSE_FILE_NAME.match(pathlib.PurePosixPath(relative_path).name):
        concerns.append(f'changes the license file {relative_path}')
    if len(LICENSE_NOTICE.findall(new_text)) < len(
        LICENSE_NOTICE.findall(old_text),
    ):
        concerns.append(f'removes license notices in {relative_path}')
    if set(LICENSE_METADATA.findall(old_text)) != set(
        LICENSE_METADATA.findall(new_text),
    ):
        concerns.append(f'changes license metadata in {relative_path}')
    return concerns


def _shell_concerns(command: str) -> list[str]:
    """Describe why a shell command needs the operator's decision.

    :param command: The shell command about to run.
    :returns: The concerns, if any.
    """
    if SHELL_LICENSE_TARGET.search(command):
        return ['the command deletes, moves or rewrites a license file']
    return []


def _explain(concerns_summary: str) -> str:
    """Explain to the operator why their decision is needed.

    :param concerns_summary: The concerns, joined into one string.
    :returns: The prompt shown to the operator.
    """
    return (
        "License terms are the maintainer's decision "
        f'(see {POLICY_DOC}): {concerns_summary}. '
        'The agent must have presented this change to you first.'
    )


def main() -> int:
    """Read the hook input and ask the operator when needed.

    :returns: The process exit code.
    """
    return hook_utils.run_hook(_edit_concerns, _shell_concerns, _explain)


if __name__ == '__main__':
    sys.exit(main())
