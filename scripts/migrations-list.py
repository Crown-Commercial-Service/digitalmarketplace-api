#!/usr/bin/env python
# encoding: utf-8

import sys

from alembic.script import ScriptDirectory


def version_history(migrations_path):
    migrations = ScriptDirectory(migrations_path)
    version_history = [m.revision for m in migrations.walk_revisions()]
    version_history.reverse()
    return version_history


if __name__ == '__main__':
    for version in version_history(sys.argv[1]):
        print(version)
