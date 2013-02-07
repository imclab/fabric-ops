#!/usr/bin/env python

# :copyright: (c) 2013 by AndYet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

from fabric.operations import *
from fabric.api import *
from fabric.contrib.files import *
from fabric.colors import *
from fabric.context_managers import cd

import common

_version  = '1.2.6'
_tarball  = 'nginx-%s.tar.gz' % _version
_url      = 'http://nginx.org/download/%s' % _tarball
_tmp_dir  = '/tmp/nginx-%s' % _version
_username = 'nginx'

@task
def download():
    """
    Download and extract the nginx tarball
    """
    with cd('/tmp'):
        run('wget %s' % _url)
        run('tar xf %s' % _tarball)

@task
def build():
    """
    Run ./configure for nginx and then make
    """
    if exists(_tmp_dir):
        with cd(_tmp_dir):
            run('./configure --conf-path=/etc/nginx/nginx.conf --pid-path=/var/run/nginx.pid --user=nginx --with-http_stub_status_module')
            run('make')

@task
def install(force=False):
    """
    Install nginx
    Download, extract, configure and install nginx if the nginx
    user does not already exist.

    Force install by calling as nginx.install:true
    """
    if not force and common.user_exists(_username):
        print('nginx user already exists, skipping nginx install')
    else:
        download()
        build()
        if exists(_tmp_dir):
            sudo('useradd --system %s' % _username)
            with cd(_tmp_dir):
                sudo('make install')

    upload_template('templates/nginx/nginx.conf', '/etc/nginx/nginx.conf', 
                    context=env.nginx,
                    use_sudo=True)
    sudo('chown root:root /etc/nginx/nginx.conf')

    for p in ['ops-common', 'sites-available', 'sites-enabled']:
        if not exists('/etc/nginx/%s' % p):
            sudo('mkdir /etc/nginx/%s' % p)

    for f in common.list_files('templates/nginx/ops-common'):
        upload_template(os.path.join('templates/nginx/ops-common', f), '/etc/nginx/ops-common',
                        context=env.nginx,
                        use_sudo=True)
        sudo('chown root:root /etc/nginx/ops-common/%s' % f)

@task
def site(siteconfig):
    print('do something useful here')
