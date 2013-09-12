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
import fabops.redis


_major_version = '2.0'
_minor_version = '.0-p247'

_version    = '%s%s' % (_major_version, _minor_version)
_tarball    = 'ruby-%s.tar.gz' % _version
_tmp_dir    = '/tmp/ruby-%s' % _version
_target_dir = '/home/kochiku'
_username   = 'kochiku'
_url        = 'https://ftp.ruby-lang.org/pub/ruby/2.0/%s' % _tarball

@task
def enable_runit():
    cfg = { 'name':        'kochiku',
            'deploy_user': 'kochiku',
            'logDir':      '/var/log/kochiku'
          }

    execute('fabops.runit.update_app', cfg, runTemplate='templates/kochiku/kochiku.run', 
                                            logrunTemplate='templates/kochiku/kochiku.logrun', 
                                            logconfigTemplate='templates/kochiku/kochiku.logconfig')

@task
def install(cfg, force=False):
    """
    Install kochiku
    install kochiku if the kochiku user does not already exist.

    Force install by calling as kochiku.install:true
    """
    if not fabops.common.user_exists(_username):
        # for p in ('openjdk-7-jre', 'unzip'):
        #     fabops.common.install_package(p)
        sudo('useradd --system %s' % _username)

    if force:
        sudo('rm -f /tmp/%s' % _tarball)
        if exists(_target_dir):
            sudo('rm -rf %s' % _target_dir)
        if cfg['broker']:
            sudo('rm -f /tmp/%s' % _es_tarball)
            if exists(_es_dir):
                sudo('rm -rf %s' % _es_dir)

    if not exists(_tmp_dir):
        with cd('/tmp'):
            if not exists('/tmp/%s' % _tarball):
                run('wget %s' % _url)
                run('tar xf %s' % _tarball)

        with cd(_tmp_dir):
            run('./configure')
            run('make')
            run('make install')

    execute('fabops.redis.deploy', 'redisApi', cfg)
