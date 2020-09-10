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


def _parse_line(line, gitdir, root, filepath, winid):
    line = line.replace("'", '', 1)
    line = line.rstrip("'")
    pattern = re.compile(r"(\*|\|)\s+([0-9A-Za-z]{6,13})\s-\s")
    match = re.search(pattern, line)
    if not match:
        return None
    return {
        'word': line,
        'source__commit': match.group(2),
        'source__gitdir': gitdir,
        'source__root': root,
        'source__file': filepath,
        'source__winid': winid
    }


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
        context['__gitdir'] = self.vim.call('denite#git#gitdir')
        if not context['__gitdir']:
            return
        context['__root'] = self.vim.call('denite#git#root', context['__gitdir'])
        if not context['__root']:
            return

        args = dict(enumerate(context['args']))
        is_all = str(args.get(0, [])) == 'all'
        context['pattern'] = context['input'] if context['input'] else str(args.get(1, ''))
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

        self.vim.command(r'syntax match deniteSource__gitlogRef /\v((\*\||)\s)@<=[0-9A-Za-z]{7,13}(\s-\s)@=/ '
                         r'contained containedin=deniteSource__gitlogHeader '
                         r'nextgroup=deniteSource__gitlogTag,deniteSource__gitlogTime')
        self.vim.command(r'syntax match deniteSource__gitlogTag /(.\{-}tag:\s.\{-})/ contained '
                         r'containedin=' + self.syntax_name + ' '
                         r'nextgroup=deniteSource__gitlogTime')
        self.vim.command(r'syntax match deniteSource__gitlogTime /([^)]\{-}\sago)/ contained '
                         r'containedin=' + self.syntax_name + ' '
                         r'nextgroup=deniteSource__gitlogUser')
        self.vim.command(r'syntax match deniteSource__gitlogUser /\v\<[^<]+\>$/ contained '
                         r'containedin=' + self.syntax_name)

    def gather_candidates(self, context):
        if context['__proc']:
            return self.__async_gather_candidates(context, 0.03)
        if not context['__root']:
            return []
        args = []
        args += ['git', '--git-dir=' + context['__gitdir']]
        args += ['--no-pager', 'log']
        args += self.vars['default_opts']
        if len(context['__file']):
            git_file = os.path.relpath(
                os.path.join(context['__root'], context['__file']),
                os.path.dirname(context['__gitdir']),
            )
            args += ['--', git_file]

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

        filepath = context['__file']
        winid = context['__winid']
        for line in outs:
            result = _parse_line(
                line, context['__gitdir'], context['__root'], filepath, winid
            )
            if not result:
                continue
            candidates.append(result)
        return candidates


class Kind(Openable):
    def __init__(self, vim):
        super().__init__(vim)

        self.persist_actions = ['reset', 'preview']
        self.redraw_actions = ['reset']
        self.name = 'gitlog'

    def action_delete(self, context):
        target = context['targets'][0]
        commit = target['source__commit']
        bufname = '[Git %s]' % (commit)
        if self.vim.call('bufexists', bufname):
            bufnr = self.vim.call('bufnr', bufname)
            self.vim.command('bdelete ' + str(bufnr))
            return

        winid = target['source__winid']
        self.vim.call('win_gotoid', winid)
        option = {
                'gitdir': target['source__gitdir'],
                'edit': 'vsplit'
                }
        self.vim.call('denite#git#diffCurrent', commit, option)

    def action_reset(self, context):
        target = context['targets'][0]
        commit = target['source__commit']
        gitdir = target['source__gitdir']

        c = str(self.vim.call('denite#util#input',
                        'Reset mode mixed|soft|hard [m/s/h]: ',
                        '',
                        ''))
        opt = ''
        if c == 'm':
            opt = '--mixed'
        elif c == 's':
            opt = '--soft'
        elif c == 'h':
            opt = '--hard'
        else:
            return
        self.vim.call('denite#git#reset', opt + ' ' + commit, gitdir)

    def action_open(self, context, split=None):
        target = context['targets'][0]
        commit = target['source__commit']
        gitdir = target['source__gitdir']
        winid = target['source__winid']
        is_all = True if not target['source__file'] else False
        option = {
                'all': 1 if is_all else 0,
                'gitdir': gitdir,
                'fold': 0
                }
        if split is not None:
            option['edit'] = split
        if not is_all:
            option['file'] = os.path.relpath(
                os.path.join(target['source__root'], target['source__file']),
                os.path.dirname(gitdir),
            )
        self.vim.call('win_gotoid', winid)
        self.vim.call('denite#git#show', commit, option)

    def action_split(self, context):
        return self.action_open(context, 'split')

    def action_vsplit(self, context):
        return self.action_open(context, 'vsplit')

    def __get_preview_window(self):
        return next(filterfalse(lambda x:
                                not x.options['previewwindow'],
                                self.vim.windows), None)

    def action_preview(self, context):
        target = context['targets'][0]
        commit = target['source__commit']
        gitdir = target['source__gitdir']
        suffix = commit + ']]'
        preview_window = self.__get_preview_window()
        if preview_window:
            same = preview_window.buffer.name.endswith(suffix)
            self.vim.command('pclose!')
            if same:
                return

        prev_id = self.vim.call('win_getid')
        winid = target['source__winid']
        is_all = True if not target['source__file'] else False
        option = {
            'all': 1 if is_all else 0,
            'gitdir': gitdir
        }
        option['edit'] = 'vsplit' if context['vertical_preview'] else 'split'
        option['floating_preview'] = int(context['floating_preview'])
        if option['floating_preview'] == 1:
            pos = self.vim.call('win_screenpos', prev_id)
            winwidth = self.vim.call('winwidth', 0)
            option['preview_win_row'] = pos[0] - 1
            option['preview_win_col'] = (pos[1] - 1) + winwidth - context['preview_width']
            option['preview_width'] = context['preview_width']
            option['preview_height'] = context['preview_height']
        if not is_all:
            option['file'] = os.path.relpath(
                os.path.join(target['source__root'], target['source__file']),
                os.path.dirname(gitdir),
            )
        self.vim.call('denite#git#show', commit, option)
        self.vim.command('setl previewwindow')
        if not is_all:
            self.vim.command('set nofen')
        self.vim.call('win_gotoid', prev_id)

