"""Allowlisted configuration edits; never execute generated code or cloud commands."""
import difflib
import re


def propose(files):
    after = dict(files)
    changes = []
    for path, source in files.items():
        updated = source
        # Only exact, unambiguous line replacements. Do not infer ports/users/CIDRs.
        if path.endswith(('.yaml', '.yml')):
            updated = re.sub(r'^(\s*privileged:\s*)true(\s*(?:#.*)?)$', r'\g<1>false\2', updated, flags=re.M)
            updated = re.sub(r'^(\s*hostNetwork:\s*)true(\s*(?:#.*)?)$', r'\g<1>false\2', updated, flags=re.M)
        if path.endswith('.tf'):
            updated = re.sub(r'^(\s*encrypted\s*=\s*)false(\s*(?:#.*)?)$', r'\g<1>true\2', updated, flags=re.M)
            updated = re.sub(r'^(\s*acl\s*=\s*)"public-read(?:-write)?"(\s*(?:#.*)?)$', r'\g<1>"private"\2', updated, flags=re.M)
        after[path] = updated
        if updated != source:
            changes.append({'path': path, 'diff': ''.join(difflib.unified_diff(
                source.splitlines(True), updated.splitlines(True), fromfile=path, tofile=path+'.proposed'))})
    return {'files': after, 'changes': changes,
            'scope': 'versioned workspace configuration only; does not modify a repository or live infrastructure',
            'warning': 'Hardening can change workload behavior. Review the diff and test the resulting configuration.'}
