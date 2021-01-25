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
from itertools import filterfalse
from .base import Base
from denite import util
from ..kind.file import Kind as File

EMPTY_LINE = re.compile(r"^\s*$")
STATUS_MAP = {
    ' ': ' ',
    'M': '~',
    'T': '~',
    'A': '+',
    'D': '-',
    'R': '→',
    'C': 'C',
    'U': 'U',
    '?': '?'}


def _parse_line(line, gitdir, root, winnr):
    path = os.path.join(root, line[3:])
    index_symbol = STATUS_MAP[line[0]]
    tree_symbol = STATUS_MAP[line[1]]
    word = "{0}{1} {2}".format(index_symbol, tree_symbol, line[3:])
    return {
        'word': word,
        'action__path': path,
        'source__gitdir': gitdir,
        'source__root': root,
        'Source__winnr': winnr,
        'source__staged': index_symbol not in [' ', '?'],
        'source__tree': tree_symbol not in [' ', '?']
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


class Source(Base):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'gitstatus'
        self.kind = Kind(vim)
        self.is_public_context = True

    def on_init(self, context):
        context['__gitdir'] = self.vim.call('denite#git#gitdir')
        if not context['__gitdir']:
            return
        context['__root'] = os.path.dirname(context['__gitdir'])
        context['__winnr'] = self.vim.call('winnr')

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
        gitdir = context['__gitdir']
        if not gitdir:
            return []
        root = context['__root']
        if not root:
            return []
        winnr = context['__winnr']
        args = ['git', 'status', '--porcelain', '-uall']
        self.print_message(context, ' '.join(args))
        lines = run_command(args, root)
        candidates = []

        for line in lines:
            if EMPTY_LINE.fullmatch(line):
                continue
            candidates.append(_parse_line(line, gitdir, root, winnr))

        return candidates


class Kind(File):
    def __init__(self, vim):
        super().__init__(vim)

        self.persist_actions += ['reset', 'add', 'delete']  # pylint: disable=E1101
        self.redraw_actions += ['reset', 'add', 'commit']  # pylint: disable=E1101
        self.name = 'gitstatus'
        self._previewed_target = None

        val = self.vim.call('exists', ':Rm')
        if val == 2:
            self.remove = 'rm'
        elif self.vim.call('executable', 'rmtrash'):
            self.remove = 'rmtrash'
        else:
            self.remove = 'delete'

    def action_patch(self, context):
        args = []
        root = context['targets'][0]['source__root']
        for target in context['targets']:
            filepath = target['action__path']
            args.append(os.path.relpath(filepath, root))
        self.vim.command('terminal git add ' + ' '.join(args) + ' --patch')

    def action_add(self, context):
        args = ['git', 'add']
        root = context['targets'][0]['source__root']
        for target in context['targets']:
            filepath = target['action__path']
            args.append(os.path.relpath(filepath, root))
        run_command(args, root)

    def __get_preview_window(self):
        return next(filterfalse(lambda x:
                                not x.options['previewwindow'],
                                self.vim.windows), None)

    # diff action
    def action_delete(self, context):
        target = context['targets'][0]
        root = target['source__root']
        winnr = target['Source__winnr']
        gitdir = target['source__gitdir']

        preview_window = self.__get_preview_window()

        if preview_window:
            self.vim.command('pclose!')
            if self._previewed_target == target:
                return

        relpath = os.path.relpath(target['action__path'], root)
        prefix = ''
        if target['source__staged']:
            if target['source__tree']:
                confirmed = str(self.vim.call('denite#util#input',
                                'Diff cached?[y/n]',
                                'y',
                                '')) == 'y'
                if confirmed == 'y':
                    prefix = '--cached '
            else:
                prefix = '--cached '
        prev_id = self.vim.call('win_getid')
        self.vim.command(str(winnr) + 'wincmd w')
        self.vim.call('denite#git#diffPreview', prefix, relpath, gitdir)

        self.vim.call('win_gotoid', prev_id)
        self._previewed_target = target

    def action_reset(self, context):
        cwd = os.path.normpath(self.vim.eval('expand("%:p:h")'))
        for target in context['targets']:
            filepath = target['action__path']
            root = target['source__root']
            path = os.path.relpath(filepath, root)
            if target['source__tree'] and target['source__staged']:
                res = str(self.vim.call('denite#util#input',
                                'Select action reset or checkout [r/c]',
                                '',
                                ''))
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
            self.vim.command('checktime')

    def action_commit(self, context):
        root = context['targets'][0]['source__root']
        files = []
        for target in context['targets']:
            filepath = target['action__path']
            files.append(os.path.relpath(filepath, root))
        self.vim.call('denite#git#commit', '-v', files)

