#!/usr/bin/env python

# :copyright: (c) 2013 by &yet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

from fabric.operations import *
from fabric.api import *
from fabric.contrib.files import *
from fabric.colors import *
from fabric.context_managers import cd

import fabops.common

_tarballs = (('skalibs-1.3.0.tar.gz', 'skalibs'), ('execline-1.2.2.tar.gz', 'execline'), ('s6-1.0.0.tar.gz', 's6'))
_url      = 'http://skarnet.org/software/'


@task
def download():
    """
    Download and extract the tarball
    """
    with cd('/package'):
        for s, t in _tarballs:
            if exists(s):
                sudo('rm -f %s' % s)
            sudo('wget %s/%s/%s' % (_url, t, s))
            sudo('tar xf %s' % _tarball)

@task
def install(force=False):
    """
    Install s6 and it's required packages
    Download, extract, configure and install s6

    Force install by calling as stun.install:true
    """
    if not force and exists(_work_dir):
        print('s6 is already installed')
    else:
        download()
        with cd(_work_dir):
            sudo('make install')
