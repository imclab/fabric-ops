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

_major_version = '2.6'
_minor_version = '.10'

_version  = '%s%s' % (_major_version, _minor_version)
_tarball  = 'redis-%s.tar.gz' % _version
_tmp_dir  = '/tmp/redis-%s' % _version
_username = 'redis'
_url      = 'http://redis.googlecode.com/files/%s' % _tarball


@task
def download():
    """
    Download and extract the redis tarball
    """
    with cd('/tmp'):
        run('wget %s' % _url)
        run('tar xf %s' % _tarball)

@task
def build():
    """
    Run ./configure for redis and then make
    """
    if exists(_tmp_dir):
        with cd(_tmp_dir):
            run('make')

@task
def install(force=False, qa=False):
    """
    Install redis
    Download, extract, configure and install redis if the redis
    user does not already exist.

    Force install by calling as redis.install:true

    qa should be set to True when provisioning a non-production
       server, it controls what data volume is used
         False == /data/redis
         True  == /var/lib/redis
    """
    if not force and fabops.common.user_exists(_username):
        print('redis user already exists, skipping redis install')
    else:
        for p in ('build-essential',):
            fabops.common.install_package(p)

        download()
        build()
        if exists(_tmp_dir):
            if not fabops.common.user_exists(_username):
                sudo('useradd --system %s' % _username)

            sudo('mkdir -p /usr/local/sbin')
            with cd(_tmp_dir):
                sudo('make install')
                for s in ('redis-check-aof', 'redis-check-dump', 'redis-cli', 'redis-server'):
                    if exists(s):
                        sudo('mv %s /usr/local/sbin/' % s)

    if not exists('/etc/redis'):
        sudo('mkdir /etc/redis')

    if qa:
        datadir = '/var/lib/redis'
    else:
        datadir = env.redis['datadir']

    for d in (env.redis['logdir'], env.redis['piddir'], datadir):
        if not exists(d):
            sudo('mkdir %s' % d)
        sudo('chown %s:%s %s' % (_username, _username, d))

@task
def deploy(rolename, qa=False):
    if rolename in env.redis['ports']:
        install(qa=qa)

        if qa:
            dataroot = '/var/lib/redis'
        else:
            dataroot = env.redis['datadir']

        d            = env.redis
        d['port']    = env.redis['ports'][rolename]
        s            = 'redis_%s' % d['port']
        datadir      = os.path.join(dataroot, s)
        d['datadir'] = datadir

        upload_template('templates/redis/redis.conf', '/etc/redis/%s.cfg' % s, 
                        context=d,
                        use_sudo=True)
        sudo('chown root:root /etc/redis/%s.cfg' % s)

        upload_template('templates/redis/upstart.conf', '/etc/init/%s.conf' % s, 
                        context=d,
                        use_sudo=True)

        if exists('/etc/monit/conf.d'):
            upload_template('templates/monit/redis.conf', '/etc/monit/conf.d/redis_%s.conf' % d['port'],
                            context=d,
                            use_sudo=True)
