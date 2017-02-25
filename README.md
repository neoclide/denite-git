# Denite-git

[![](http://img.shields.io/github/issues/chemzqm/denite-git.svg)](https://github.com/chemzqm/denite-git/issues)
[![](http://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![](https://img.shields.io/badge/doc-%3Ah%20vim--run.txt-red.svg)](doc/denite-git.txt)

Git log, git status and git changed source for [Denite.nvim](https://github.com/Shougo/denite.nvim).

Video of denite gitlog:

[![asciicast](https://asciinema.org/a/104395.png)](https://asciinema.org/a/104395)

Video of denite gitstatus:

[![asciicast](https://asciinema.org/a/104410.png)](https://asciinema.org/a/104410)

## Installation

For user of [vim-plug](https://github.com/junegunn/vim-plug), add:

    Plug 'Shougo/denite.nvim'
    Plug 'chemzqm/vim-easygit'
    Plug 'chemzqm/denite-git'

For user of [dein.vim](https://github.com/Shougo/dein.vim), add:

    call dein#add('Shougo/denite.nvim')
    call dein#add('chemzqm/vim-easygit')
    call dein#add('chemzqm/denite-git')

to your vimrc and run `PlugInstall` if needed.

## Usage

For git log:

``` vim
" log of current file
Denite gitlog

" all git log of current repository
Denite gitlog:all

" filter gitlog with fix as input
Denite gitlog::fix
```

For git status:

``` vim
Denite gitstatus
```

For git changed

``` vim
Denite gitchanged
```

`gitchanged` source is just simple line source.

## Actions

Actions of gitlog:

* `open` default action for open seleted commit.
* `preview` preview seleted commit.
* `delete` run git diff with current commit for current buffer. (just named delete)
* `reset` run git reset with current commit.

Actions of git status:

* `open` open seleted file, default action
* `add` run git add for seleted file(s).
* `delete` run git diff for seleted file. (just named delete)
* `reset` run git reset/checkout or remove for seleted file(s).
* `commit` run git commit for seleted file(s).

## Key Mapppings

It's recommanded to add custom key mappings for improve your speed of
interacting with denite source, for example:

``` viml
call denite#custom#map(
      \ 'normal',
      \ 'a',
      \ '<denite:do_action:add>',
      \ 'noremap'
      \)

call denite#custom#map(
      \ 'normal',
      \ 'd',
      \ '<denite:do_action:delete>',
      \ 'noremap'
      \)

call denite#custom#map(
      \ 'normal',
      \ 'r',
      \ '<denite:do_action:reset>',
      \ 'noremap'
      \)
```

## LICENSE

Copyright 2017 chemzqm@gmail.com

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
