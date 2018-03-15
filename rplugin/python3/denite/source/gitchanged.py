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
            if i in changed:
                lines.append({
                    'word': x,
                    'abbr': (fmt % (i + 1, x)),
                    'action__path': context['__bufname'],
                    'action__line': (i + 1)
                    })

        return lines
