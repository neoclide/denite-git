
function! denite#git#gitdir() abort
  let gitdir = get(b:, 'git_dir', '')
  if !empty(gitdir) | return gitdir | endif
  let path = (empty(bufname('%')) || &buftype =~# '^\%(nofile\|acwrite\|quickfix\|terminal\)$') ? getcwd() : expand('%:p')
  let dir = finddir('.git', path.';')
  if empty(dir) | return '' | endif
  let files = findfile('.git', path.';',-1)
  if empty(files) | return fnamemodify(dir, ':p:h') | endif
  return fnamemodify(files[-1], ':p')
endfunction

function! denite#git#root(gitdir) abort
  let out = systemlist('git --git-dir='.a:gitdir.' rev-parse --show-toplevel')
  if v:shell_error
    return v:null
  endif
  return out[0]
endfunction

function! denite#git#commit(prefix, files) abort
  if get(g:, 'loaded_fugitive', 0)
    execute 'Gcommit '.a:prefix .' ' . join(map(a:files, 'fnameescape(v:val)'), ' ')
  elseif get(g:, 'did_easygit_loaded', 0)
    call easygit#commit(a:prefix . ' '. join(a:files, ' '))
  else
    execute 'terminal  git commit '.a:prefix. ' '. join(map(a:files, 'fnameescape(v:val)'), ' ')
  endif
endfunction

function! denite#git#diffPreview(prefix, file, gitdir) abort
  let file = tempname()
  call system('git --no-pager --git-dir='.a:gitdir.' diff '.a:prefix. ' ' . fnameescape(a:file). ' > '.file)
  if v:shell_error
    return
  endif
  execute 'vs +setl\ previewwindow '.file
  setl filetype=diff
  setl nofoldenable
endfunction

function! denite#git#reset(args, gitdir) abort
  call system('git --git-dir='.a:gitdir.' reset '.a:args)
  if v:shell_error | return | endif
  checktime
endfunction

function! denite#git#diffCurrent(revision, option) abort
  let gitdir = get(a:option, 'gitdir', '')
  if empty(gitdir) | return | endif
  let ref = len(a:revision) ? a:revision : 'head'
  let edit = a:0 ? a:1 : 'vsplit'
  let ft = &filetype
  let bnr = bufnr('%')
  let root = fnamemodify(gitdir, ':h')
  let file = substitute(expand('%:p'), root . '/', '', '')
  let command = 'git --no-pager --git-dir='. gitdir
      \. ' show --no-color '
      \. ref . ':' . file
  let edit = get(a:option, 'edit', 'edit')
  let output = system(command)
  let list = split(output, '\v\r?\n')
  if !len(list)| diffoff | return | endif
  diffthis
  execute 'keepalt '.edit.' +setl\ buftype=nofile [[Git '.a:revision.']]'
  call setline(1, list[0])
  silent! call append(1, list[1:])
  execute 'setf ' . ft
  diffthis
  let b:git_dir = gitdir
  setl foldenable
  call setwinvar(winnr(), 'easygit_diff_origin', bnr)
  call setpos('.', [bufnr('%'), 0, 0, 0])
endfunction

function! denite#git#show(args, option)
  let fold = get(a:option, 'fold', 1)
  let gitdir = get(a:option, 'gitdir', '')
  let showall = get(a:option, 'all', 0)
  if empty(gitdir) | return | endif
  let format = "--pretty=format:'".s:escape("commit %H%nparent %P%nauthor %an <%ae> %ad%ncommitter %cn <%ce> %cd%n %e%n%n%s%n%n%b")."' "
  if showall
    let command = 'git --no-pager --git-dir=' . gitdir
      \. ' show  --no-color ' . format . a:args
  else
    let root = fnamemodify(gitdir, ':h')
    let file = get(a:option, 'file', '')
    let command = 'git --no-pager --git-dir=' . gitdir
      \. ' show --no-color ' . format . a:args . ' -- ' . file
  endif
  let edit = get(a:option, 'edit', 'edit')
  let output = system(command)
  let list = split(output, '\v\r?\n')
  if !len(list)| return | endif
  execute 'keepalt '.edit.' +setl\ buftype=nofile [[Git '.a:args.']]'
  call setline(1, list[0])
  silent! call append(1, list[1:])
  setlocal filetype=git foldmethod=syntax readonly bufhidden=wipe
  if !showall
    setl nofoldenable
  endif
  if get(a:option, 'floating_preview', 0) && exists('*nvim_win_set_config')
      call nvim_win_set_config(win_getid(), {
           \ 'relative': 'editor',
           \ 'row': a:option.preview_win_row,
           \ 'col': a:option.preview_win_col,
           \ 'width': a:option.preview_width,
           \ 'height': a:option.preview_height,
           \ })
        doautocmd User denite-preview
  endif
  call setpos('.', [bufnr('%'), 7, 0, 0])
  exe 'nnoremap <buffer> <silent> u :call <SID>ShowParentCommit()<cr>'
  exe 'nnoremap <buffer> <silent> d :call <SID>ShowNextCommit()<cr>'
  let b:git_dir = gitdir
endfunction

function! s:ShowParentCommit() abort
  let commit = matchstr(getline(2), '\v\s\zs.+$')
  if empty(commit) | return | endif
  call denite#git#show(commit, {
        \ 'eidt': 'edit',
        \ 'gitdir': b:git_dir,
        \ 'all': 1,
        \})
endfunction

function! s:ShowNextCommit() abort
  let commit = matchstr(getline(1), '\v\s\zs.+$')
  let commit = s:NextCommit(commit, b:git_dir)
  if empty(commit) | return | endif
  call denite#git#show(commit, {
        \ 'eidt': 'edit',
        \ 'gitdir': b:git_dir,
        \ 'all': 1,
        \})
endfunction

function! s:NextCommit(commit, gitdir) abort
  let output = system('git --git-dir=' . a:gitdir
        \. ' log --reverse --ancestry-path '
        \. a:commit . '..master | head -n 1 | cut -d \  -f 2')
  if v:shell_error && output !=# ""
    echohl Error | echon output | echohl None
    return
  endif
  return substitute(output, '\n', '', '')
endfunction

function! s:winshell() abort
  return &shell =~? 'cmd' || exists('+shellslash') && !&shellslash
endfunction

function! s:escape(str)
  if s:winshell()
    let cmd_escape_char = &shellxquote == '(' ?  '^' : '^^^'
    return substitute(a:str, '\v\C[<>]', cmd_escape_char, 'g')
  endif
  return a:str
endfunction
