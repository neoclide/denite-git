# ============================================================================
# FILE: gitstatus.py
# AUTHOR: Qiming Zhao <chemzqm@gmail.com>
# License: MIT license
# ============================================================================
# pylint: disable=E0401,C0411
import os
import re
import subprocess
import shlex
from .base import Base
from denite import util
from ..kind.file import Kind as File

EMPTY_LINE = re.compile(r"^\s*$")
STATUS_MAP = {
    ' ': ' ',
    'M': '~',
    'A': '+',
    'D': '-',
    'R': '→',
    'C': 'C',
    'U': 'U',
    '?': '?'}

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
    index_symbol = STATUS_MAP[line[0]]
    tree_symbol = STATUS_MAP[line[1]]
    word = "{0}{1} {2}".format(index_symbol, tree_symbol, line[3:])
    return {
        'word': word,
        'action__path': path,
        'source__root': root,
        'source__staged': index_symbol not in [' ', '?'],
        'source__tree': tree_symbol not in [' ', '?']
    }


def run_command(commands, cwd):
    try:
        p = subprocess.run(commands,
                           cwd=cwd,
                           encoding="utf8",
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return []
    return p.stdout.split('\n')

class Source(Base):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'gitstatus'
        self.kind = Kind(vim)

    def on_init(self, context):
        cwd = self.vim.call('getcwd')

        context['__root'] = _find_root(cwd)

    def highlight(self):
        self.vim.command('highlight deniteGitStatusAdd guifg=#009900 ctermfg=2')
        self.vim.command('highlight deniteGitStatusChange guifg=#bbbb00 ctermfg=3')
        self.vim.command('highlight deniteGitStatusDelete guifg=#ff2222 ctermfg=1')
        self.vim.command('highlight deniteGitStatusUnknown guifg=#5f5f5f ctermfg=59')

    def define_syntax(self):
        self.vim.command(r'syntax match deniteGitStatusHeader /^.*$/ ' +
                         r'containedin=' + self.syntax_name)
        self.vim.command(r'syntax match deniteGitStatusSymbol /^\s*\zs\S\+/ ' +
                         r'contained containedin=deniteGitStatusHeader')
        self.vim.command(r'syntax match deniteGitStatusAdd /+/ ' +
                         r'contained containedin=deniteGitStatusSymbol')
        self.vim.command(r'syntax match deniteGitStatusDelete /-/ ' +
                         r'contained containedin=deniteGitStatusSymbol')
        self.vim.command(r'syntax match deniteGitStatusChange /\~/ ' +
                         r'contained containedin=deniteGitStatusSymbol')
        self.vim.command(r'syntax match deniteGitStatusUnknown /?/ ' +
                         r'contained containedin=deniteGitStatusSymbol')

    def gather_candidates(self, context):
        root = context['__root']
        if not root:
            return []
        args = ['git', 'status', '--porcelain', '-uall']
        self.print_message(context, ' '.join(args))
        lines = run_command(args, root)
        candidates = []

        for line in lines:
            if EMPTY_LINE.fullmatch(line):
                continue
            candidates.append(_parse_line(line, root))

        return candidates


class Kind(File):
    def __init__(self, vim):
        super().__init__(vim)

        self.persist_actions += ['reset', 'add'] #pylint: disable=E1101
        self.redraw_actions += ['reset', 'add', 'commit'] #pylint: disable=E1101
        self.name = 'gitstatus'

        val = self.vim.call('exists', ':Rm')
        if val == 2:
            self.remove = 'rm'
        elif self.vim.call('executable', 'rmtrash'):
            self.remove = 'rmtrash'
        else:
            self.remove = 'delete'

    def action_add(self, context):
        args = ['git', 'add']
        root = context['targets'][0]['source__root']
        for target in context['targets']:
            filepath = target['action__path']
            args.append(os.path.relpath(filepath, root))
        run_command(args, root)

    # diff action
    def action_delete(self, context):
        target = context['targets'][0]
        root = target['source__root']
        relpath = os.path.relpath(target['action__path'], root)
        prefix = ''
        if target['source__staged']:
            if target['source__tree']:
                if util.input(self.vim, context, 'Diff cached?[y/n]', 'y') == 'y':
                    prefix = '--cached '
            else:
                prefix = '--cached '
        self.vim.call('easygit#diffShow', prefix + relpath, 'bot split')

    def action_reset(self, context):
        cwd = self.vim.call('getcwd')
        for target in context['targets']:
            filepath = target['action__path']
            root = target['source__root']
            path = os.path.relpath(filepath, root)
            if target['source__tree'] and target['source__staged']:
                res = util.input(self.vim, context, 'Select action reset or checkout [r/c]')
                if res == 'c':
                    args = 'git checkout -- ' + path
                    run_command(shlex.split(args), root)
                elif res == 'r':
                    args = 'git reset HEAD -- ' + path
                    run_command(shlex.split(args), root)
            elif target['source__tree']:
                args = 'git checkout -- ' + path
                run_command(shlex.split(args), root)
            elif target['source__staged']:
                args = 'git reset HEAD -- ' + path
                run_command(shlex.split(args), root)
            else:
                if self.remove == 'rm':
                    self.vim.command('Rm ' + os.path.relpath(filepath, cwd))
                elif self.remove == 'rmtrash':
                    run_command(['rmtrash', filepath], root)
                else:
                    self.vim.call('delete', filepath)

    def action_commit(self, context):
        root = context['targets'][0]['source__root']
        args = ['-v']
        for target in context['targets']:
            filepath = target['action__path']
            path = os.path.relpath(filepath, root)
            args.append(path)
        self.vim.call('easygit#commit', ' '.join(args))
