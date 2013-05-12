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

_version   = '%s%s' % (_major_version, _minor_version)
_tarball   = 'haproxy-%s.tar.gz' % _version
_tmp_dir   = '/tmp/haproxy-%s' % _version
_cfg_root  = '/etc/haproxy'
_site_root = '%s/conf.d' % _cfg_root
_username  = 'haproxy'
_configure = ' '.join(['TARGET=linux26',
                       'USE_OPENSSL=1',
                       ' USE_PCRE=1',
                      ])

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
            run('make %s' % _configure)

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
        for p in ('build-essential', 'libssl-dev', 'libpcre3-dev', 'zlib1g-dev'):
            fabops.common.install_package(p)

        download()
        build()
        if exists(_tmp_dir):
            sudo('useradd --system %s' % _username)
            with cd(_tmp_dir):
                sudo('make install')

    if not exists('/etc/haproxy'):
        sudo('mkdir %s'          % _cfg_root)
        sudo('mkdir %s/errors'   % _cfg_root)
        sudo('mkdir %s/ssl-keys' % _cfg_root)
        sudo('mkdir %s/conf.d'   % _cfg_root)

    env.haproxy['ssl-key'] = '/etc/haproxy/ssl-keys/%s' % env.haproxy['keyfile']

    upload_template('templates/haproxy/haproxy.base', '%s/haproxy.base' % _cfg_root, 
                    context=env.haproxy,
                    use_sudo=True)
    sudo('chown root:root %s/haproxy.base' % _cfg_root)

    put('keys/%s' % env.haproxy['keyfile'], env.haproxy['ssl-key'], use_sudo=True)

    upload_template('templates/haproxy/503-error.http', '%s/errors/503-error.http' % _cfg_root, 
                    context=env.haproxy,
                    use_sudo=True)
    sudo('chown root:root %s/errors/503-error.http' % _cfg_root)

    upload_template('templates/haproxy/upstart.conf', '/etc/init/haproxy.conf', 
                    context=env.haproxy,
                    use_sudo=True)

@task
def install_site(siteName, siteConfig):
    if not fabops.common.user_exists(_username):
        install()

    if fabops.common.user_exists(_username):
        cfg = fabops.common.flatten(siteConfig)
        cfgFile = '%s.cfg' % os.path.join(_site_root, cfg['name'])
        upload_template(os.path.join(siteConfig['site_config_dir'], '%s.haproxy' % cfg['name']),
                        cfgFile,
                        context=cfg,
                        use_sudo=True)
        sudo('chown root:root %s' % cfgFile)

        if not exists('%s/haproxy.acls' % _cfg_root):
            sudo('touch %s/haproxy.acls' % _cfg_root)
        if not exists('%s/haproxy.uses' % _cfg_root):
            sudo('touch %s/haproxy.uses' % _cfg_root)

        if 'haproxy.acls' in cfg:
            for s in cfg['haproxy.acls']:
                append('%s/haproxy.acls' % _cfg_root, s, use_sudo=True)

        if 'haproxy.uses' in cfg:
            for s in cfg['haproxy.uses']:
                append('%s/haproxy.uses' % _cfg_root, s, use_sudo=True)

        sudo('cat %(cfgRoot)s/haproxy.base %(cfgRoot)s/haproxy.acls %(cfgRoot)s/haproxy.uses %(siteRoot)s/*.cfg > %(cfgRoot)s/haproxy.cfg' % {'cfgRoot': _cfg_root, 'siteRoot': _site_root})
