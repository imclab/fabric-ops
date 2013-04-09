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
_package  = 'riak_%s-1_i386.deb' % _version
_tmp_dir  = '/tmp/riak-%s' % _version
_username = 'riak'
_url      = 'http://downloads.basho.com.s3-website-us-east-1.amazonaws.com/riak/%s/%s/ubuntu/lucid/%s' % (_major_version, _version, _package)


@task
@roles('monit')
def post_install():
    pass
    # if exists('/etc/monit/conf.d'):
    #     upload_template('templates/monit/riak.conf', '/etc/monit/conf.d/riak',
    #                     context=d,
    #                     use_sudo=True)


@task
def install(force=False):
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

    for d in (env.riak['logdir'], env.riak['piddir'], env.riak['datadir']):
        if not exists(d):
            sudo('mkdir %s' % d)
        sudo('chown riak:riak %s' % d)

    # we are unable to use upload_template because riak's config file
    # is nothing *but* python format string dilly-doos - ugh
    put('templates/riak/riak.conf', '/etc/riak/app.config', use_sudo=True)
