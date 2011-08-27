# GitSuperRepository.py
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

"""
==========================
GitSuperRepository Package
==========================

The GitSuperRepository package provides the GitSuperRepository class, which
presents an Python interface to a git repository. This repository may contain
submodules which are stored upstream in various version control systems
including git, mercurial and svn.
"""

from __future__ import print_function

import pprint, sys, os, re
from subprocess import call

# subprocess.check_output is only available in newer Python versions
try:
    from subprocess import check_output
except ImportError:
    def check_output(x, bufsize=0, executable=None, stdin=None, stdout=None, stderr=None, preexec_fn=None, close_fds=False, shell=False, cwd=None, env=None, universal_newlines=False, startupinfo=None, creationflags=0):
        """Emulate the check_output function provided in newer versions of Python."""
        return subprocess.Popen(x, bufsize, executable, stdin, subprocess.PIPE, stderr, preexec_fn, close_fds, shell, cwd, env, universal_newlines, startupinfo, creationflags).communicate()[0]

class GitSuperRepository():
    """
    Creating a GitSuperRepository object binds the object to a specific git
    repository.
    """
    def __init__(self, path=None):
        """
        Create a GitSuperRepository object to manage a git repository.

        The root of the git repository is assumed to be 'path'. If this is not
        specified, then it is assumed to be the current working directory.
        """

        if(path == None):
            path = os.path.abspath(os.curdir)

        self.__path    = path
        self.__git_dir = os.path.join(path, '.git')

        # Check we have a git repository
        if not os.path.isdir(self.__git_dir):
            raise ValueError(self.__git_dir + ' is not a git repository')

    def __num_lines(self, test):
        """Count the number of lines in a string."""
        for i, l in enumerate(test.split('\n')):
            pass
        return i + 1

    def git_command(self, command, module=None):
        """Execute a git command on the repository."""
        if module == None:
            git_dir   = '--git-dir=' + self.__git_dir
            work_tree = '--work-tree=' + self.__path
            return check_output(['git', git_dir, work_tree] + command).rstrip('\n')
        else:
            self.assert_is_submodule(module)
            module_abspath =  os.path.join(self.__path, module)
            git_dir   = '--git-dir=' + os.path.join(module_abspath, '.git')
            work_tree = '--work-tree=' + module_abspath
            return check_output(['git', git_dir, work_tree] + command, cwd=module_abspath).rstrip('\n')

    def config(self, command, module=None, file=None):
        """Configure the repository."""
        if file != None:
            command = ['--file=' + file] + command
        return self.git_command(['config'] + command, module)

    def get_gitmodules_config(self, module, option):
        """Get a gitmodules configuration option for a submodule."""
        return self.config(['submodule.' + module + '.' + option],
                            file='.gitmodules')

    def set_gitmodules_config(self, module, option, value):
        """Set a gitmodules configuration option for a submodule."""
        return self.config(['submodule.' + module + '.' + option, value],
                            file='.gitmodules')

    def is_submodule(self, path):
        """Check if path is a submodule."""
        output = self.git_command(['ls-files', '--stage', '--', path])

        if(self.__num_lines(output) != 1):
            return False
        if output[0:6] == '160000':
            return True
        else:
            return False

    def assert_is_submodule(self, path):
        """Raise an exception if path is not a valid submodule."""
        if not self.is_submodule(path):
            raise ValueError('Error: ' + path + ' is not a submodule.')

    def upstream_type(self, path):
        """Get version control system used by upstream repository."""
        return self.get_gitmodules_config(path, 'upstreamtype')

    def upstream_url(self, path):
        """Get URL of upstream repository."""
        return self.get_gitmodules_config(path, 'upstreamurl')

    def revision(self, path):
        """Get branch of upstream repository which should be tracked by a submodule."""
        return self.get_gitmodules_config(path, 'revision')

    def set_upstream_type(self, path, type):
        """Set version control system used by upstream repository."""
        self.set_gitmodules_config(path, 'upstreamtype', type)

    def set_upstream_url(self, path, url):
        """Set URL of upstream repository."""
        self.set_gitmodules_config(path, 'upstreamurl', url)

    def set_revision(self, path, revision):
        """Set branch of upstream repository which should be tracked by a submodule."""
        self.set_gitmodules_config(path, 'revision', revision)

    def upstream_init(self, path):
        """Initialise a submodule for pushing patches upstream."""
        self.assert_is_submodule(path)

        path = path.rstrip('/')
        type = self.upstream_type(path)
        url  = self.upstream_url(path)

        print('Initialising submodule ' + type + ' upstream repository for ' + path + '\nwith upstream URL ' + url)

        if type == 'svn':
            rev = self.revision(path)
            self.git_command(['checkout', rev], module=path)
            self.git_command(['svn', 'init', '-s', '--prefix=origin/', url], module=path)
            self.git_command(['svn', 'fetch'], module=path)
        elif type == 'git':
            self.git_command(['remote', 'add', 'upstream', url], module=path)
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
            print('Unknown upstream repository type: ' + type)
        return

    def mv_submodule(self, old, new):
        """Move a submodule."""
        self.assert_is_submodule(old)

        self.config(['--rename-section', 'submodule.'+old, 'submodule.'+new])
        self.config(['--rename-section', 'submodule.'+old, 'submodule.'+new], file='.gitmodules')
        self.config(['submodule.'+new+'.path', new], file='.gitmodules')
        self.git_command(['rm', '--cached', old])
        os.rename(old, new)
        self.git_command(['add', new])
        self.git_command(['add', '.gitmodules'])

    def rm_submodule(self, old):
        """Remove a submodule."""
        self.assert_is_submodule(old)
        self.config(['--remove-section', 'submodule.'+old])
        self.config(['--remove-section', 'submodule.'+old], file='.gitmodules')
        self.git_command(['rm', '--cached', old])
        self.git_command(['add', '.gitmodules'])

    def add_submodule(self, path, url, upstreamurl, type, revision):
        """Add a submodule."""
        check_output(['git', 'submodule', 'add', url, path])
        self.set_upstream_url(path, upstreamurl)
        self.set_upstream_type(path, type)
        self.set_revision(path, revision)
        self.git_command(['add', '.gitmodules'])

    def list_submodules(self):
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

    def list_branches(self, module=None):
        """
        List all local branches. If module is not 'None', list all branches
        in that submodule.
        """
        res = self.git_command(['branch', '--no-color'], module).splitlines()
        branches = []
        for branch in res:
            branchname = branch.strip(' *')
            if branchname != '(no branch)':
                branches.append(branch.strip(' *'))
        return branches

    def remote_status(self, module, branch):
        """
        For the specified branch, lists the commits which are different between
        the local and the tracked upstream version of that branch.
        """
        try:
            remote = self.config(['branch.'+branch+'.remote'], module)
        except:
            # If the branch doesn't have a remote then return an empty list
            return []
        remote_ref = self.config(['branch.'+branch+'.merge'], module)
        remote_branch = re.sub('^refs/heads/', '', remote_ref)
        return self.git_command(['rev-list', '--oneline', '--left-right',
            branch+'...'+remote+'/'+remote_branch], module).splitlines()

    def checkout_modules(self, modules):
        """Checkout a list of submodules to the branches they should be tracking."""
        print('Checking out branches in submodules:')
        for module in modules:
            rev = self.revision(module)
            print('  ' + module + ': ' + rev)
            self.git_command(['checkout', '-q', rev], module)

    def pull_ff(self, modules):
        """Do a fast-forward only pull of a list of submodules."""
        print('Updating local branches where possible:')
        for module in modules:
            rev = self.revision(module)
            print('  ' + module + ': ' + rev)
            self.git_command(['pull', '--ff-only', '-q'], module)

    def fetch_modules(self, modules):
        """Fetch a list of submodules from their remotes."""
        print('Getting updates for submodules:')
        for module in modules:
            print('  ' + module)
            self.git_command(['fetch', '-q'], module)
