# ============================================================================
# FILE: gitfiles.py
# AUTHOR: tylerc230@gmail.com
# License: MIT license
# ============================================================================
# pylint: disable=E0401,C0411
import os
import re
import subprocess
from .base import Base as BaseSource
from ..kind.base import Base as BaseKind
from ..kind.openable import Kind as Openable
from denite import util
from denite.util import debug


EMPTY_LINE = re.compile(r"^\s*$")
def run_command(commands, cwd, encoding='utf-8'):
    try:
        p = subprocess.run(commands,
                           cwd=cwd,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return []

    return p.stdout.decode(encoding).split('\n')


class Source(BaseSource):

    def __init__(self, vim):
        super().__init__(vim)
        self.name = "gitfiles"
        self.kind = GitObject(vim)

    def on_init(self, context):
        winnr = self.vim.call('winnr')

        gitdir = self.vim.call('denite#git#gitdir')
        context['__root'] = '' if not gitdir else os.path.dirname(gitdir)
        context['__winnr'] = winnr

    def gather_candidates(self, context):
        args = ['git', 'ls-tree', '-r', 'master']
        root = context['__root']
        self.print_message(context, ' '.join(args))
        lines = run_command(args, root)
        return [self._parse_line(line, root) for line in lines if not EMPTY_LINE.fullmatch(line)]

    def _parse_line(self, line, root):
        parts = line.split("\t", 1)
        filename = parts[1]
        obj_sha = parts[0].split(" ")[2]
        path = os.path.join(root, filename)
        return {
                'word': obj_sha,
                'abbr': path
                }


class GitObject(Openable):
    def __init__(self, vim):
        super().__init__(vim)

    def action_open(self, context):
        debug(self.vim, context)
        target = context['targets'][0]
        obj_sha = target["word"]
        self.vim.command("new | r !git cat-file -p " + obj_sha)

