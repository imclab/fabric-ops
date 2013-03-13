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
@roles('redis_api')
def install(force=False):
    """
    Install redis
    Download, extract, configure and install redis if the redis
    user does not already exist.

    Force install by calling as redis.install:true
    """
    if not force and fabops.common.user_exists(_username):
        print('redis user already exists, skipping redis install')
    else:
        for p in ('build-essential',):
            fabops.common.install_package(p)

        download()
        build()
        if exists(_tmp_dir):
            sudo('useradd --system %s' % _username)
            with cd(_tmp_dir):
                sudo('make install')
                for s in ('redis-check-aof', 'redis-check-dump', 'redis-cli', 'redis-server'):
                    sudo('mv %s /usr/local/sbin/')

    if not exists('/etc/redis'):
        sudo('mkdir /etc/redis')

    for d in (env.redis['logdir'], env.redis['piddir'], env.redis['datadir']):
        if not exists(d):
            sudo('mkdir %s' % d)
        sudo('chown redis:redis %s' % d)

    ports = []
    # loop thru the roles for the host, find that role in
    # the redis global config and extract the port number
    if env.host_string in env.roledefs['redis_api']:
        ports.append(env.redis['ports']['redis_api'])

    for p in ports:
        d         = env.redis
        d['port'] = p
        s         = 'redis_%s' % p
        datadir   = os.path.join(env.redis['datadir'], p)

        upload_template('templates/redis/redis.conf', '/etc/redis/%s.cfg' % s, 
                        context=d,
                        use_sudo=True)
        sudo('chown root:root /etc/redis/%s.cfg' % s)

        upload_template('templates/redis/upstart.conf', '/etc/init/%s.conf' % s, 
                        context=d,
                        use_sudo=True)

        if not exists(datadir):
            sudo('mkdir %s' % datadir)
        sudo('chown redis:redis %s' % datadir)

@task
@roles('redis_api')
def setup():
    execute(install)
