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
def enable_runit():
    cfg = { 'name':        'prosody',
            'deploy_user': 'prosody',
            'logDir':      '/var/log/prosody'
          }

    execute('fabops.runit.update_app', cfg, runTemplate='templates/prosody/prosody.run', 
                                            logrunTemplate='templates/prosody/prosody.logrun', 
                                            logconfigTemplate='templates/prosody/prosody.logconfig')

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

        for p in ('lua-zlib', 'lua-sec-prosody', 'lua-dbi-sqlite3', 'liblua5.1-bitop-dev', 'liblua5.1-bitop0', 'prosody'):
            fabops.common.install_package(p)

        append('/etc/prosody/prosody.cfg.lua', 'Include "conf.d/*.cfg.lua"', use_sudo=True)
        append('/etc/prosody/prosody.cfg.lua', 'daemonize=false;', use_sudo=True)

        sudo('touch /etc/prosody/installed.txt')

    for d in ('/var/log/prosody', '/etc/prosody/conf.d'):
        if not exists(d):
            sudo('mkdir %s' % d)

    enable_runit()

@task
def deploy(projectConfig):
    if not exists('/etc/prosody/installed.'):
        install(projectConfig)

    siteConfig = '/etc/prosody/conf.d/%s.cfg.lua' % projectConfig['name']

    upload_template(os.path.join(projectConfig['configDir'], '%s.prosody' % projectConfig['name']),
                    siteConfig,
                    context=projectConfig,
                    use_sudo=True)
    sudo('chown root:root %s' % siteConfig)

    if 'prosody.ssl_cert' in projectConfig:
        put(os.path.join(env.our_path, 'keys', projectConfig['prosody.ssl_cert']), 
            '/etc/prosody/certs/%s' % projectConfig['prosody.ssl_cert'], use_sudo=True)
    if 'prosody.ssl_cert_key' in projectConfig:
        put(os.path.join(env.our_path, 'keys', projectConfig['prosody.ssl_cert_key']), 
            '/etc/prosody/certs/%s' % projectConfig['prosody.ssl_cert_key'], use_sudo=True)

    if 'prosody.modules' in projectConfig:
        targetDir    = os.path.join('/home', projectConfig['deploy_user'], projectConfig['deploy_dir'])
        deployBranch = projectConfig['deploy_branch']

        with settings(user=projectConfig['deploy_user']):
            run('ssh-add -D; ssh-add .ssh/%s' % projectConfig['deploy_key'])
            run('rm -rf %s' % targetDir)
            run('git clone %s %s' % (projectConfig['repository.url'], projectConfig['deploy_dir']))

            with cd(targetDir):
                run('git fetch')

        for m in projectConfig['prosody.modules']:
            sudo('rm -rf /usr/lib/prosody/modules/%s' % m)
            sudo('ln -s %s/%s /usr/lib/prosody/modules/%s' % (targetDir, m, m))

        upload_template(os.path.join(projectConfig['configDir'], 'andyet.json'),
                '/etc/prosody/andyet.json',
                context=projectConfig,
                use_sudo=True)

    sudo('sv restart prosody')
