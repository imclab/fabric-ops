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

_os_version = 'precise'


@task
def install(cfg, force=False):
    """
    Install redis
    Download, extract, configure and install redis if the redis
    user does not already exist.

    Force install by calling as redis.install:true
    """
    if not force and exists('/etc/prosody/installed.txt'):
        print('prosody is already installed, skipping install step')
    else:
        append('/etc/apt/sources.list', 'deb http://packages.prosody.im/debian %s main' % _os_version, use_sudo=True)

        sudo('wget https://prosody.im/files/prosody-debian-packages.key -O- | sudo apt-key add -')

        sudo('apt-get update')

        fabops.common.install_package('prosody')

        # if exists('/etc/prosody'):

    if not exists('/var/log/prosody'):
        sudo('mkdir /var/log/prosody')

@task
def deploy(projectConfig):
    if not exists('/etc/prosody/installed.'):
        install(projectConfig)

    siteConfig = '/etc/prosody/conf.d/%s.lua' % projectConfig['name']

    upload_template(os.path.join(projectConfig['configDir'], '%s.prosody' % projectConfig['name']),
                    siteConfig,
                    context=projectConfig,
                    use_sudo=True)
    sudo('chown root:root %s' % siteConfig)

    if 'prosody.ssl_cert' in projectConfig:
        put(os.path.join(env.our_path, 'keys', projectConfig['prosody.ssl_cert']), 
            '/etc/prosody/%s' % projectConfig['prosody.ssl_cert'], use_sudo=True)
    if 'prosody.ssl_cert_key' in projectConfig:
        put(os.path.join(env.our_path, 'keys', projectConfig['prosody.ssl_cert_key']), 
            '/etc/prosody/%s' % projectConfig['prosody.ssl_cert_key'], use_sudo=True)

    sudo('sv restart prosody')
