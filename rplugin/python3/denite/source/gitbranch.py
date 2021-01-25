# ============================================================================
# FILE: gitbranch.py
# AUTHOR: Takahiro Shirasaka <tk.shirasaka@gmail.com>
# License: MIT license
# ============================================================================
# pylint: disable=E0401,C0411
import os
import re
import subprocess
from .base import Base as BaseSource
from ..kind.base import Base as BaseKind
from denite import util

EMPTY_LINE = re.compile(r"^\s*$")


def _parse_line(line, root):
    current_symbol = line[0]
    return {
        'word': line,
        'action__path': line[2:],
        'source__root': root,
        'source__branch': line[10:] if line[2:10] == 'remotes/' else line[2:],
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
        gitdir = self.vim.call('denite#git#gitdir')
        context['__root'] = os.path.dirname(gitdir)

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

        self.persist_actions += []  # pylint: disable=E1101
        self.redraw_actions += []  # pylint: disable=E1101
        self.name = 'gitbranch'
        self.default_action = 'checkout'

    def action_checkout(self, context):
        target = context['targets'][0]
        branch = target['source__branch']
        args = ['git', 'checkout', branch]
        root = target['source__root']
        run_command(args, root)
        self.vim.command('bufdo e')

    def action_delete(self, context):
        target = context['targets'][0]
        args = []
        root = target['source__root']
        branch = target['source__branch']

        if target['source__remote']:
            branchname = branch.split('/')[-1]

            confirm = str(self.vim.call('denite#util#input',
                            'Delete remote branch ' + branchname + '? [y/n] : ',
                            'n',
                            '')) == 'y'
            if confirm:
                args = ['git', 'push', 'origin', '--delete', branchname]
        else:
            force = str(self.vim.call('denite#util#input',
                            'Force delete? [y/n] : ',
                            'n',
                            '')) == 'y'
            args = ['git', 'branch', '-D' if force else '-d', branch]

        if len(args) > 0:
            run_command(args, root)
            self.vim.command('bufdo e')

    def action_merge(self, context):
        target = context['targets'][0]
        root = target['source__root']
        branch = target['source__branch']
        args = ['git', 'merge', branch]

        if not target['source__current']:
            run_command(args, root)
            self.vim.command('bufdo e')

    def action_rebase(self, context):
        target = context['targets'][0]
        branch = target['source__branch']
        args = ['git', 'rebase', branch]
        root = target['source__root']

        if not target['source__current']:
            run_command(args, root)
            self.vim.command('bufdo e')

