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


_major_version = '1.1'
_minor_version = '.13'

_version    = '%s%s' % (_major_version, _minor_version)
_tarball    = 'logstash-%s-flatjar.jar' % _version
_tmp_dir    = '/tmp/logstash-%s' % _version
_target_dir = '/opt/logstash'
_username   = 'logstash'
_url        = 'https://logstash.objects.dreamhost.com/release/%s' % _tarball

_es_version = '0.20.6'
_es_tarball = 'elasticsearch-%s.zip' % _es_version
_es_url     = 'https://download.elasticsearch.org/elasticsearch/elasticsearch/%s' % _es_tarball
_es_dir     = '/opt/es'

@task
def enable_runit():
    cfg = { 'name':        'logstash',
            'deploy_user': 'logstash',
            'logDir':      '/var/log/logstash'
          }

    execute('fabops.runit.update_app', cfg, runTemplate='templates/logstash/logstash.run', 
                                            logrunTemplate='templates/logstash/logstash.logrun', 
                                            logconfigTemplate='templates/logstash/logstash.logconfig')

@task
def install(cfg, force=False):
    """
    Install logstash
    install logstash if the logstash user does not already exist.

    Force install by calling as logstash.install:true
    """
    if not fabops.common.user_exists(_username):
        for p in ('openjdk-7-jre', 'unzip'):
            fabops.common.install_package(p)
        sudo('useradd --system %s' % _username)

    if force:
        sudo('rm -f /tmp/%s' % _tarball)
        if exists(_target_dir):
            sudo('rm -rf %s' % _target_dir)
        if cfg['broker']:
            sudo('rm -f /tmp/%s' % _es_tarball)
            if exists(_es_dir):
                sudo('rm -rf %s' % _es_dir)

    with cd('/tmp'):
        if not exists('/tmp/%s' % _tarball):
            run('wget %s' % _url)
        if cfg['broker'] and not exists('/tmp/%s' % _es_tarball):
            run('wget --no-check-certificate %s' % _es_url)

    if not exists('/etc/logstash'):
        sudo('mkdir -p /etc/logstash')
        sudo('mkdir -p /var/log/logstash')

    if not exists(_target_dir):
        sudo('mkdir -p %s' % _target_dir)
        sudo('cp /tmp/%s %s/' % (_tarball, _target_dir))
        sudo('ln -s %s/%s %s/logstash.jar' % (_target_dir, _tarball, _target_dir))

    if cfg['broker'] and not exists(_es_dir):
        sudo('mkdir -p %s' % _es_dir)
        sudo('unzip /tmp/%s -d %s' % (_es_tarball, _es_dir))

    enable_runit()

    sudo('chown -R %s:%s %s' % (_username, _username, _target_dir))

    if cfg['broker']:
        sudo('chown -R %s:%s %s' % (_username, _username, _es_dir))
        execute('fabops.redis.deploy', 'redisApi', cfg)
