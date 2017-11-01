# ============================================================================
# FILE: gitbranch.py
# AUTHOR: Takahiro Shirasaka <tk.shirasaka@gmail.com>
# License: MIT license
# ============================================================================
# pylint: disable=E0401,C0411
import os
import re
import subprocess
import shlex
from .base import Base as BaseSource
from ..kind.base import Base as BaseKind
from denite import util

EMPTY_LINE = re.compile(r"^\s*$")

def _find_root(path):
    while True:
        if path == '/' or os.path.ismount(path):
            return None
        p = os.path.join(path, '.git')
        if os.path.isdir(p):
            return path
        path = os.path.dirname(path)


def _parse_line(line, root):
    path = os.path.join(root, line[3:])
    current_symbol = line[0]
    return {
        'word': line,
        'action__path': line[2:],
        'source__root': root,
        'source__current': current_symbol == '*',
        'source__remote': line[2:10] == 'remotes/',
    }

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

        self.name = 'gitbranch'
        self.kind = Kind(vim)

    def on_init(self, context):
        cwd = os.path.normpath(self.vim.eval('expand("%:p:h")'))

        context['__root'] = _find_root(cwd)

    def gather_candidates(self, context):
        root = context['__root']
        if not root:
            return []
        args = ['git', 'branch', '--no-color', '-a']
        self.print_message(context, ' '.join(args))
        lines = run_command(args, root)
        candidates = []

        for line in lines:
            if EMPTY_LINE.fullmatch(line):
                continue
            candidates.append(_parse_line(line, root))

        return candidates


class Kind(BaseKind):
    def __init__(self, vim):
        super().__init__(vim)

        self.persist_actions += ['open', 'delete']  # pylint: disable=E1101
        self.redraw_actions += ['open', 'delete']  # pylint: disable=E1101
        self.name = 'gitbranch'
        self.default_action = 'open'

    def action_open(self, context):
        target = context['targets'][0]
        args = ['git', 'checkout']
        root = target['source__root']
        path = target['action__path']

        if target['source__remote'] : path = path[8:]
        args.append(path)

        run_command(args, root)

    def action_delete(self, context):
        target = context['targets'][0]
        args = []
        root = target['source__root']
        path = target['action__path']

        force = util.input(self.vim, context, 'Force delete? [y/n] : ', 'n') == 'y'

        if target['source__remote']:
            if force == True:
                args ['git', 'push', 'origin', ':' + target['action__path'][8:]]
        else:
            args = ['git', 'branch', '-D' if force == True else '-d', target['action__path']]

        if len(args) > 0 : run_command(args, root)

    def action_merge(self, context):
        target = context['targets'][0]
        args = ['git', 'merge', target['action__path']]
        root = target['source__root']

        if target['source__remote'] == False and target['source__current'] == False:
            run_command(args, root)
