"""Reuse the official linter's pinned SDK artifact in Direct Mode."""
from pathlib import Path
import shutil
artifact='genvm-universal-v0.3.0-rc7.tar.xz'
source=Path.home()/'.cache/genvm-linter'/artifact
target=Path.home()/'.cache/gltest-direct'/artifact
if not source.exists():raise SystemExit('Run genvm-lint check contracts/runbook_latch.py first.')
target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists():shutil.copyfile(source,target)
print('Pinned SDK archive ready.')
