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

_major_version = '1.2'
_minor_version = '.1'

_version  = '%s%s' % (_major_version, _minor_version)
_package  = 'riak_%s-1_amd64.deb' % _version
_tmp_dir  = '/tmp/riak-%s' % _version
_username = 'riak'
_url      = 'http://downloads.basho.com.s3-website-us-east-1.amazonaws.com/riak/%s/%s/ubuntu/precise/%s' % (_major_version, _version, _package)


@task
@roles('monit')
def post_install():
    pass
    # if exists('/etc/monit/conf.d'):
    #     upload_template('templates/monit/riak.conf', '/etc/monit/conf.d/riak',
    #                     context=d,
    #                     use_sudo=True)


@task
def install(force=False, qa=False):
    """
    Install riak
    Prepare Ubuntu to install Riak from the basho repository

    Force install by calling as riak.install:true
    """
    if not force and fabops.common.user_exists(_username):
        print('riak user already exists, skipping riak install')
    else:
        if not fabops.common.user_exists(_username):
            sudo('useradd --system %s' % _username)

        fabops.common.install_package('libssl0.9.8')

        with cd('/tmp'):
            run('wget %s' % _url)
            sudo('dpkg -i %s' % _package)

    if not exists('/etc/riak'):
        sudo('mkdir /etc/riak')

    if qa:
        datadir = '/var/lib/redis'
    else:
        datadir = env.riak['datadir']

    for d in (env.riak['logdir'], env.riak['piddir'], datadir):
        if not exists(d):
            sudo('mkdir %s' % d)
        sudo('chown %s:%s %s' % (_username, _username, d))

@task
def deploy(qa=False):
    install(qa=qa)

    if qa:
        dataroot = '/var/lib/riak'
    else:
        dataroot = env.riak['datadir']

    d            = env.riak
    d['datadir'] = dataroot
    
    # we are unable to use upload_template because riak's config file
    # is nothing *but* python format string dilly-doos - ugh
    put('templates/riak/riak.conf', '/etc/riak/app.config', use_sudo=True)

    # do not believe we need an upstart script as the riak deb installs one
    # but I kept this here in case we decide to change things later
    # upload_template('templates/riak/upstart.conf', '/etc/init/%s.conf' % s, 
    #                 context=d,
    #                 use_sudo=True)

    if exists('/etc/monit/conf.d'):
        upload_template('templates/monit/riak.conf', '/etc/monit/conf.d/riak.conf',
                        context=d,
                        use_sudo=True)

