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

"""A class for simplifying the management of a git repository containing
   submodules which may be stored upstream in various version control systems,
   including git, mercurial and svn."""

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
    """Manage a git super-repository containing submodules."""
    def __init__(self, path=None):
        """Create a GitSuperRepository object to manage a git repository.

        The root of the git repository is assumed to be 'path'. If this is not
        specified, then it is assumed to be the current working directory."""

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

    def git_command(self, command):
        """Execute a git command on the repository."""
        git_dir   = '--git-dir=' + self.__git_dir
        return check_output(['git', git_dir] + command).rstrip('\n')

    def config(self, command):
        """Configure the repository."""
        return self.git_command(['config'] + command)

    def module_config(self, command):
        """Configure the .gitmodules file."""
        return self.git_command(['config', '--file=.gitmodules'] + command)

    def get_module_config(self, module, option):
        """Get an option for a submodule."""
        return self.module_config(['submodule.' + module + '.' + option])

    def set_module_config(self, module, option, value):
        """Set an option for a submodule."""
        return self.module_config(['submodule.' + module + '.' + option, value])

    def is_submodule(self, path):
        """Check if path is a submodule."""
        output = self.git_command(['ls-files', '--stage', '--', path])

        if(self.__num_lines(output) != 1):
            return False
        if output[0:6] == '160000':
            return True
        else:
            return False

    def upstream_type(self, path):
        """Get version control system used by upstream repository."""
        return self.get_module_config(path, 'upstreamtype')

    def upstream_url(self, path):
        """Get URL of upstream repository."""
        return self.get_module_config(path, 'upstreamurl')

    def revision(self, path):
        """Get branch of upstream repository which should be tracked by a submodule."""
        return self.get_module_config(path, 'revision')

    def set_upstream_type(self, path, type):
        """Set version control system used by upstream repository."""
        self.set_module_config(path, 'upstreamtype', type)

    def set_upstream_url(self, path, url):
        """Set URL of upstream repository."""
        self.set_module_config(path, 'upstreamurl', url)

    def set_revision(self, path, revision):
        """Set branch of upstream repository which should be tracked by a submodule."""
        self.set_module_config(path, 'revision', revision)

    def upstream_init(self, path):
        """Initialise a submodule for pushing patches upstream."""
        if not self.is_submodule(path):
            print('Error: ' + path + ' is not a submodule.')
            return

        path = path.rstrip('/')
        type = self.upstream_type(path)
        url  = self.upstream_url(path)

        git_dir   = '--git-dir=' + os.path.join(path, '.git')
        work_tree = '--work-tree=' + path

        print 'Initialising submodule ' + type + ' upstream repository for ' + path + '\nwith upstream URL ' + url

        if type == 'svn':
            rev = self.revision(path)
            self.git_command([work_tree, 'checkout', rev])
            self.git_command([work_tree, 'svn', 'init', '-s', '--prefix=origin/', url])
            self.git_command([work_tree, 'svn', 'fetch'])
        elif type == 'git':
            self.git_command([work_tree, 'remote', 'add', 'upstream', url])
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

    def mv_submodule(self, old, new):
        """Move a submodule."""
        if not self.is_submodule(old):
            print('Error: ' + old + ' is not a submodule.')
            return
        self.config(['--rename-section', 'submodule.'+old, 'submodule.'+new])
        self.module_config(['--rename-section', 'submodule.'+old, 'submodule.'+new])
        self.module_config(['submodule.'+new+'.path', new])
        self.git_command(['rm', '--cached', old])
        os.rename(old, new)
        self.git_command(['add', new])
        self.git_command(['add', '.gitmodules'])

    def rm_submodule(self, old):
        """Remove a submodule."""
        if not self.is_submodule(old):
            print('Error: ' + old + ' is not a submodule.')
            return
        self.config(['--remove-section', 'submodule.'+old])
        self.module_config(['--remove-section', 'submodule.'+old])
        self.git_command(['rm', '--cached', old])
        self.git_command(['add', '.gitmodules'])

    def init_module(self, path):
        """Initialise a submodule."""
        if not self.is_submodule(old):
            print('Error: ' + old + ' is not a submodule.')
            return
        path = path.rstrip('/')
        git_dir = '--git-dir=' + os.path.join(path, '.git')
        work_tree = '--work-tree=' + path

        print 'Initialising submodule ' + path

        rev = self.revision(path)
        call(['git', git_dir, work_tree, 'checkout', rev])

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

    def checkout_modules(self, modules):
        """Checkout a list of submodules to the branches they should be tracking."""
        print 'Checking out branches in submodules:'
        for module in modules:
            if not self.is_submodule(module):
                raise ValueError
            rev = self.revision(module)
            git_dir = '--git-dir=' + os.path.join(module, '.git')
            work_tree = '--work-tree=' + module
            print '  ' + module + ': ' + rev
            call(['git', git_dir, work_tree, 'checkout', '-q', rev])

    def pull_ff(self, modules):
        """Do a fast-forward only pull of a list of submodules."""
        print 'Updating local branches where possible:'
        for module in modules:
            rev = self.revision(module)
            git_dir = '--git-dir=' + os.path.join(module, '.git')
            work_tree = '--work-tree=' + module
            print '  ' + module + ': ' + rev
            call(['git', 'pull', '--ff-only', '-q'], cwd=module)

    def fetch_modules(self, modules):
        """Fetch a list of submodules from their remotes."""
        print 'Getting updates for submodules:'
        for module in modules:
            git_dir = '--git-dir=' + os.path.join(module, '.git')
            print '  ' + module
            call(['git', git_dir, 'fetch', '-q'])
