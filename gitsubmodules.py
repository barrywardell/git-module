# gitsubmodules.py
#
# A collection of python functions for simplifying the management of a
# git repository containing submodules
#
# Copyright (C) 2011 Barry Wardell <barry.wardell@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA.

import pprint, subprocess, sys, os, re
from subprocess import call

def __check_output(x, bufsize=0, executable=None, stdin=None, stdout=None, stderr=None, preexec_fn=None, close_fds=False, shell=False, cwd=None, env=None, universal_newlines=False, startupinfo=None, creationflags=0):
    """Emulate the __check_output function provided in newer versions of Python."""
    return subprocess.Popen(x, bufsize, executable, stdin, subprocess.PIPE, stderr, preexec_fn, close_fds, shell, cwd, env, universal_newlines, startupinfo, creationflags).communicate()[0]

def num_lines(test):
    """Count the number of lines in a string."""
    for i, l in enumerate(test.split('\n')):
        pass
    return i + 1

def is_submodule(path):
    """Check if path is a submodule."""
    output = __check_output(['git', 'ls-files', '--stage', '--', path]).rstrip('\n')
    if(num_lines(output) != 1):
        return False
    if output[0:6] == '160000':
        return True
    else:
        return False

def upstream_type(path):
    """Get version control system used by upstream repository."""
    return __check_output(['git', 'config', '--file=.gitmodules', 'submodule.'+path+'.upstreamtype']).rstrip('\n')

def upstream_url(path):
    """Get URL of upstream repository."""
    return __check_output(['git', 'config', '--file=.gitmodules', 'submodule.'+path+'.upstreamurl']).rstrip('\n')

def revision(path):
    """Get branch of upstream repository which should be tracked by a submodule."""
    return __check_output(['git', 'config', '--file=.gitmodules', 'submodule.'+path+'.revision']).rstrip('\n')

def set_upstream_type(path, type):
    """Set version control system used by upstream repository."""
    call(['git', 'config', '--file=.gitmodules', 'submodule.'+path+'.upstreamtype', type])

def set_upstream_url(path, url):
    """Set URL of upstream repository."""
    call(['git', 'config', '--file=.gitmodules', 'submodule.'+path+'.upstreamurl', url])

def set_revision(path, revision):
    """Set branch of upstream repository which should be tracked by a submodule."""
    call(['git', 'config', '--file=.gitmodules', 'submodule.'+path+'.revision', revision])

def upstream_init(path):
    """Initialise a submodule for pushing patches upstream."""
    if not is_submodule(path):
        print('Error: ' + path + ' is not a submodule.')
        return

    path = path.rstrip('/')
    type = upstream_type(path)
    url  = upstream_url(path)

    git_dir   = '--git-dir=' + os.path.join(path, '.git')
    work_tree = '--work-tree=' + path
    
    print 'Initialising submodule ' + type + ' upstream repository for ' + path + '\nwith upstream URL ' + url
    
    if type == 'svn':
        rev = revision(path)
        call(['git', git_dir, work_tree, 'checkout', rev])
        call(['git', git_dir, work_tree, 'svn', 'init', '-s', '--prefix=origin/', url])
        call(['git', git_dir, work_tree, 'svn', 'fetch'])
    elif type == 'git':
        call(['git', git_dir, work_tree, 'remote', 'add', 'upstream', url])
    elif type == 'hg':
        hgpath = path+'.hg'
        call(['hg', 'clone', url, hgpath])
        hgrc = open(os.path.join(hgpath,'.hg/hgrc'), 'a')
        hgrc.write('\n[path]\ngit = '+path+'\n\n[git]\nintree = 1\n')
        hgrc.close()
        call(['hg', '-R', hgpath, 'bookmark', 'master', '-r', 'default'])
        call(['hg', '-R', hgpath, 'gexport'])
        call(['hg', '-R', hgpath, 'pull', 'git'])
    else:
        print('Unknown upstream repository type: '+type)
    return

def mv_submodule(old, new):
    """Move a submodule."""
    if not is_submodule(old):
        print('Error: ' + old + ' is not a submodule.')
        return
    call(['git', 'config', '--rename-section', 'submodule.'+old, 'submodule.'+new])
    call(['git', 'config', '-f', '.gitmodules', '--rename-section', 'submodule.'+old, 'submodule.'+new])
    call(['git', 'config', '-f', '.gitmodules', 'submodule.'+new+'.path', new])
    call(['git', 'rm', '--cached', old])
    os.rename(old, new)
    call(['git', 'add', new])
    call(['git', 'add', '.gitmodules'])

def rm_submodule(old):
    """Remove a submodule."""
    if not is_submodule(old):
        print('Error: ' + old + ' is not a submodule.')
        return
    call(['git', 'config', '--remove-section', 'submodule.'+old])
    call(['git', 'config', '-f', '.gitmodules', '--remove-section', 'submodule.'+old])
    call(['git', 'rm', '--cached', old])
    call(['git', 'add', '.gitmodules'])

def init_module(path):
    """Initialise a submodule."""
    if not is_submodule(old):
        print('Error: ' + old + ' is not a submodule.')
        return
    path = path.rstrip('/')
    git_dir = '--git-dir=' + os.path.join(path, '.git')
    work_tree = '--work-tree=' + path
    
    print 'Initialising submodule ' + path
    
    rev = revision(path)
    call(['git', git_dir, work_tree, 'checkout', rev])

def list_submodules():
    """List all submodules."""
    f = open('.gitmodules')
    pattern = re.compile('\[submodule "(.*)"]')
    modules = []
    for line in f:
        module = pattern.match(line)
        if module != None:
            modules.append(module.group(1))
    f.close()
    return modules

def checkout_modules(modules):
    """Checkout a list of submodules to the branches they should be tracking."""
    print 'Checking out branches in submodules:'
    for module in modules:
        rev = revision(module)    
        git_dir = '--git-dir=' + os.path.join(module, '.git')
        work_tree = '--work-tree=' + module
        print '  ' + module + ': ' + rev
        call(['git', git_dir, work_tree, 'checkout', '-q', rev])

def pull_ff(modules):
    """Do a fast-forward only pull of a list of submodules."""
    print 'Updating local branches where possible:'
    for module in modules:
        rev = revision(module)
        git_dir = '--git-dir=' + os.path.join(module, '.git')
        work_tree = '--work-tree=' + module
        print '  ' + module + ': ' + rev
        call(['git', 'pull', '--ff-only', '-q'], cwd=module)

def fetch_modules(modules):
    """Fetch a list of submodules from their remotes."""
    print 'Getting updates for submodules:'
    for module in modules:
        git_dir = '--git-dir=' + os.path.join(module, '.git')
        print '  ' + module
        call(['git', git_dir, 'fetch', '-q'])
