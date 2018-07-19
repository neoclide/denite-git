# ============================================================================
# FILE: gitchaned.py
# AUTHOR: Qiming Zhao <chemzqm@gmail.com>
# License: MIT license
# ============================================================================
# pylint: disable=E0401,C0411
from .line import Source as Base


class Source(Base):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'gitchanged'

    def on_init(self, context):
        super().on_init(context)
        # context['__buffer'] = self.vim.current.buffer
        buf = self.vim.current.buffer
        context['__bufnr'] = buf.number
        context['__bufname'] = buf.name
        context['__gutter'] = buf.vars.get('gitgutter')

    def gather_candidates(self, context):
        if not context['__gutter']:
            return []

        hunks = context['__gutter']['hunks']
        changed = [x[2] for x in hunks]

        fmt = '%' + str(len(str(self.vim.call('line', '$')))) + 'd: %s'

        lines = []

        for [i, x] in enumerate(self.vim.call(
                'getbufline', context['__bufnr'], 1, '$')):
            # vim line number start from 1
            vim_line_num = i + 1
            if vim_line_num in changed:
                lines.append({
                    'word': x,
                    'abbr': (fmt % (vim_line_num, x)),
                    'action__path': context['__bufname'],
                    'action__line': vim_line_num
                    })

        return lines
