# ============================================================================
# FILE: gitlog.py
# AUTHOR: Qiming Zhao <chemzqm@gmail.com>
# License: MIT license
# ============================================================================
# pylint: disable=E0401,C0411
import os
import re
from itertools import filterfalse
from ..kind.openable import Kind as Openable
from denite import util, process

from .base import Base


def _parse_line(line, gitdir, filepath, winid):
    line = line.replace("'", '', 1)
    line = line.rstrip("'")
    pattern = re.compile(r"(\*|\|)\s([0-9A-Za-z]{6,13})\s-\s")
    match = re.search(pattern, line)
    if not match:
        return None
    return {
        'word': line,
        'source__commit': match.group(2),
        'source__gitdir': gitdir,
        'source__file': filepath,
        'source__winid': winid
    }


def _find_root(path):
    while True:
        if path == '/' or os.path.ismount(path):
            return None
        p = os.path.join(path, '.git')
        if os.path.isdir(p):
            return path
        path = os.path.dirname(path)


class Source(Base):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'gitlog'
        self.matchers = ['matcher_regexp']
        self.vars = {
            'default_opts': ['--graph', '--no-color',
                             "--pretty=format:'%h -%d %s (%cr) <%an>'",
                             '--abbrev-commit', '--date=relative']
        }
        self.kind = Kind(vim)

    def on_init(self, context):
        context['__proc'] = None

        args = dict(enumerate(context['args']))
        cwd = os.path.normpath(self.vim.eval('expand("%:p:h")'))

        is_all = str(args.get(0, [])) == 'all'
        context['pattern'] = context['input'] if context['input'] else str(args.get(1, ''))

        context['__root'] = _find_root(cwd)
        context['__winid'] = self.vim.call('win_getid')

        buftype = self.vim.current.buffer.options['buftype']
        fullpath = os.path.normpath(self.vim.call('expand', '%:p'))
        if fullpath and not buftype and not is_all:
            context['__file'] = os.path.relpath(fullpath, context['__root'])
        else:
            context['__file'] = ''

    def on_close(self, context):
        if context['__proc']:
            context['__proc'].kill()
            context['__proc'] = None

    def highlight(self):
        self.vim.command('highlight default link deniteSource__gitlogRef Title')
        self.vim.command('highlight default link deniteSource__gitlogTag Type')
        self.vim.command('highlight default link deniteSource__gitlogTime Keyword')
        self.vim.command('highlight default link deniteSource__gitlogUser Constant')

    def define_syntax(self):
        self.vim.command('syntax case ignore')
        self.vim.command(r'syntax match deniteSource__gitlogHeader /^.*$/ '
                         r'containedin=' + self.syntax_name)

        self.vim.command(r'syntax match deniteSource__gitlogRef /\v((\*\||)\s)@<=[0-9A-Za-z]{7,13}(\s-\s)@=/ '
                         r'contained containedin=deniteSource__gitlogHeader '
                         r'nextgroup=deniteSource__gitlogTag,deniteSource__gitlogTime')
        self.vim.command(r'syntax match deniteSource__gitlogTag /(.\{-}tag:\s.\{-})/ contained '
                         r'containedin=deniteSource__gitlogHeader '
                         r'nextgroup=deniteSource__gitlogTime')
        self.vim.command(r'syntax match deniteSource__gitlogTime /([^)]\{-}\sago)/ contained '
                         r'containedin=deniteSource__gitlogHeader '
                         r'nextgroup=deniteSource__gitlogUser')
        self.vim.command(r'syntax match deniteSource__gitlogUser /\v\<[^<]+\>$/ contained '
                         r'containedin=deniteSource__gitlogHeader')

    def gather_candidates(self, context):
        if context['__proc']:
            return self.__async_gather_candidates(context, 0.03)
        if not context['__root']:
            return []
        args = []
        args += ['git', '--git-dir=' + os.path.join(context['__root'], '.git')]
        args += ['--no-pager', 'log']
        args += self.vars['default_opts']
        if len(context['__file']):
            args += ['--', context['__file']]

        self.print_message(context, ' '.join(args))

        context['__proc'] = process.Process(args, context, context['__root'])
        return self.__async_gather_candidates(context, 0.5)

    def __async_gather_candidates(self, context, timeout):
        outs, errs = context['__proc'].communicate(timeout=timeout)
        context['is_async'] = not context['__proc'].eof()
        if context['__proc'].eof():
            context['__proc'] = None

        candidates = []

        for line in errs:
            self.print_message(context, line)

        gitdir = os.path.join(context['__root'], '.git')
        filepath = context['__file']
        winid = context['__winid']
        for line in outs:
            result = _parse_line(line, gitdir, filepath, winid)
            if not result:
                continue
            candidates.append(result)
        return candidates


class Kind(Openable):
    def __init__(self, vim):
        super().__init__(vim)

        self.persist_actions += ['reset', 'preview']  # pylint: disable=E1101
        self.redraw_actions += ['reset']  # pylint: disable=E1101
        self.name = 'gitlog'

    def action_delete(self, context):
        for target in context['targets']:
            commit = target['source__commit']
            winid = target['source__winid']
            self.vim.call('win_gotoid', winid)
            self.vim.call('easygit#diffThis', commit)

    def action_reset(self, context):
        target = context['targets'][0]
        commit = target['source__commit']
        c = util.input(self.vim, context, 'Reset mode mixed|soft|hard [m/s/h]: ')
        opt = ''
        if c == 'm':
            opt = '--mixed'
        elif c == 's':
            opt = '--soft'
        elif c == 'h':
            opt = '--hard'
        else:
            return
        self.vim.call('easygit#reset', opt + ' ' + commit)

    def action_open(self, context):
        for target in context['targets']:
            commit = target['source__commit']
            gitdir = target['source__gitdir']
            is_all = True if not target['source__file'] else False
            option = {
                'all': 1 if is_all else 0,
                'gitdir': gitdir,
            }
            if not is_all:
                option['file'] = target['source__file']
            self.vim.call('easygit#show', commit, option)
            self.vim.command('set nofen')

    def __get_preview_window(self):
        return next(filterfalse(lambda x:
                                not x.options['previewwindow'],
                                self.vim.windows), None)

    def action_preview(self, context):
        target = context['targets'][0]
        commit = target['source__commit']
        gitdir = target['source__gitdir']
        suffix = '__' + commit + '__'
        preview_window = self.__get_preview_window()
        if preview_window:
            same = preview_window.buffer.name.endswith(suffix)
            self.vim.command('pclose!')
            if same:
                return

        prev_id = self.vim.call('win_getid')
        is_all = True if not target['source__file'] else False
        option = {
            'all': 1 if is_all else 0,
            'edit': 'abo 20split',
            'gitdir': gitdir
        }
        if not is_all:
            option['file'] = target['source__file']
        self.vim.call('easygit#show', commit, option)
        self.vim.command('set previewwindow')
        self.vim.command('wincmd P')
        self.vim.command('set nofen')
        self.vim.call('win_gotoid', prev_id)
