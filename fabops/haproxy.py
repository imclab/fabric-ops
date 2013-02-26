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

_major_version = '1.5'
_minor_version = '-dev17'

_version  = '%s%s' % (_major_version, _minor_version)
_tarball  = 'haproxy-%s.tar.gz' % _version
_tmp_dir  = '/tmp/haproxy-%s' % _version
_username = 'haproxy'

if 'dev' in _minor_version:
    s = 'devel/'
else:
    s = ''
 
_url = 'http://haproxy.1wt.eu/download/%s/src/%s%s' % (_major_version, s, _tarball)


@task
def download():
    """
    Download and extract the haproxy tarball
    """
    with cd('/tmp'):
        run('wget %s' % _url)
        run('tar xf %s' % _tarball)

@task
def build():
    """
    Run ./configure for haproxy and then make
    """
    if exists(_tmp_dir):
        with cd(_tmp_dir):
            run('make TARGET=linux26')

@task
def install(force=False):
    """
    Install haproxy
    Download, extract, configure and install haproxy if the haproxy
    user does not already exist.

    Force install by calling as haproxy.install:true
    """
    if not force and fabops.common.user_exists(_username):
        print('haproxy user already exists, skipping haproxy install')
    else:
        for p in ('build-essential', 'libpcre3-dev'):
            fabops.common.install_package(p)

        download()
        build()
        if exists(_tmp_dir):
            sudo('useradd --system %s' % _username)
            with cd(_tmp_dir):
                sudo('make install')

    if not exists('/etc/haproxy'):
        sudo('mkdir /etc/haproxy')

    upload_template('templates/haproxy/haproxy.conf', '/etc/haproxy/haproxy.cfg', 
                    context=env.haproxy,
                    use_sudo=True)
    sudo('chown root:root /etc/haproxy/haproxy.cfg')

    upload_template('templates/haproxy/upstart.conf', '/etc/init/haproxy.conf', 
                    context=env.haproxy,
                    use_sudo=True)
