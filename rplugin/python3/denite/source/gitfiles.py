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
        args = dict(enumerate(context['args']))
        branch = str(args.get(0, "master"))
        gitdir = self.vim.call('denite#git#gitdir')
        context['__root'] = '' if not gitdir else os.path.dirname(gitdir)
        context['__branch'] = branch

    def gather_candidates(self, context):
        branch = context['__branch']
        args = ['git', 'ls-tree', '-r', branch]
        root = context['__root']
        lines = run_command(args, root)
        return [self._parse_line(line, root, branch) for line in lines if not EMPTY_LINE.fullmatch(line)]

    def _parse_line(self, line, root, branch):
        parts = line.split("\t", 1)
        filename = parts[1]
        obj_sha = parts[0].split(" ")[2]
        path = os.path.join(root, filename)
        return {
            'branch': branch,
            'hash': obj_sha,
                'word': path,
                'abbr': path
                }


class GitObject(BaseKind):
    def __init__(self, vim):
        super().__init__(vim)
        self.name = 'git_object'
        self.default_action = 'view'

    def action_view(self, context):
        target = context['targets'][0]
        obj_sha = target["hash"]
        branch = target['branch']
        self.vim.command("new | read ! git cat-file -p " + obj_sha )
        del self.vim.current.buffer[0] #need to remove the first line since 'read' insert a new line at the top
        self.vim.command("setl buftype=nofile nomodifiable bufhidden=wipe nobuflisted") #user a scratch buffer
        filename = os.path.basename(target["abbr"])
        self.vim.command("file (" + branch + ") " + filename)
        self.vim.command("filetype detect")

