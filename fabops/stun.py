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

_version   = '0.4.2'
_tarball   = 'restund-%s.tar.gz' % _version
_url       = 'http://www.creytiv.com/pub/%s' % _tarball
_tmp_dir   = '/tmp/restund-%s' % _version
_username  = 'restund'

_libre_version = '0.4.3'
_libre_tarball = 're-%s.tar.gz' % _libre_version
_libre_url     = 'http://www.creytiv.com/pub/%s' % _libre_tarball
_libre_tmp_dir = '/tmp/libre-%s' % _libre_version


# sudo apt-get install python-software-properties
# sudo apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 0xcbcb082a1bb943db
# sudo add-apt-repository 'deb http://mirror.jmu.edu/pub/mariadb/repo/5.5/ubuntu precise main'
#
# sudo apt-get install mariadb-server
#

# mysql root password  Q8Z93HW6ewU5zM9Cz7CGck7M72G3VBbG

@task
def download():
    """
    Download and extract the tarball
    """
    with cd('/tmp'):
        if exists(_tarball):
            run('rm -f %s' % _tarball)
        run('wget %s' % _url)
        run('tar xf %s' % _tarball)

        if exists(_libre_tarball):
            run('rm -f %s' % _libre_tarball)
        run('wget %s' % _libre_url)
        run('tar xf %s' % _libre_tarball)


@task
def build():
    """
    run the make command for libre and restund
    """
    if exists(_libre_tmp_dir):
        with cd(_libre_tmp_dir):
            run('make install')
    if exists(_tmp_dir):
        with cd(_tmp_dir):
            run('make')

@task
def install(force=False):
    """
    Install libre and then restund
    Download, extract, configure and install if the restund
    user does not already exist.

    Force install by calling as stun.install:true
    """
    if not force and fabops.common.user_exists(_username):
        print('restund user already exists, skipping stun install')
    else:
        for p in ('build-essential', 'mariadb-server', 'libmariadbclient-dev'):
            fabops.common.install_package(p)

        download()
        build()
        if exists(_tmp_dir):
            sudo('useradd --system %s' % _username)
            with cd(_tmp_dir):
                sudo('make install')

