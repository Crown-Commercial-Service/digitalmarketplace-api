#!/usr/bin/env python
# encoding: utf-8

from __future__ import print_function

import sys

from alembic.script import ScriptDirectory


def detect_heads(migrations):
    heads = migrations.get_heads()
    return heads


def version_history(migrations):
    version_history = [
        (m.revision, m.doc) for m in migrations.walk_revisions()
    ]
    version_history.reverse()
    return version_history


def main(migrations_path):
    migrations = ScriptDirectory(migrations_path)

    heads = detect_heads(migrations)
    if len(heads) > 1:
        print("Migrations directory has multiple heads due to branching: {}".format(heads), file=sys.stderr)
        sys.exit(1)

    for version in version_history(migrations):
        print("{:35} {}".format(*version))


if __name__ == '__main__':
    main('migrations/')
