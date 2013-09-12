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
_minor_version = '-dev19'

_version   = '%s%s' % (_major_version, _minor_version)
_tarball   = 'haproxy-%s.tar.gz' % _version
_tmp_dir   = '/tmp/haproxy-%s' % _version
_cfg_root  = '/etc/haproxy'
_site_root = '%s/conf.d' % _cfg_root
_username  = 'haproxy'
_configure = ' '.join(['TARGET=linux2628',
                       'USE_OPENSSL=1',
                       ' USE_PCRE=1',
                      ])

_503_header = """HTTP/1.0 503 Service Unavailable
Cache-Control: no-cache
Connection: close
Content-Type: text/html

"""

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
def enable_runit():
    cfg = { 'name':        'haproxy',
            'deploy_user': 'haproxy',
            'logDir':      '/var/log/haproxy'
          }

    execute('fabops.runit.update_app', cfg, runTemplate='templates/haproxy/haproxy.run', 
                                            logrunTemplate='templates/haproxy/haproxy.logrun', 
                                            logconfigTemplate='templates/haproxy/haproxy.logconfig')

@task
def install(cfg, force=False):
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

    sudo('mkdir -p /var/log/haproxy')
    sudo('chown root:root /var/log/haproxy')

    enable_runit()

@task
def install_site(projectName, projectConfig):
    if not fabops.common.user_exists(_username):
        install(projectConfig)

    if fabops.common.user_exists(_username):
        configFile = os.path.join(_site_root, '%s.cfg' % projectConfig['name'])
        upload_template(os.path.join(projectConfig['configDir'], '%s.haproxy' % projectConfig['name']),
                        configFile,
                        context=projectConfig,
                        use_sudo=True)
        sudo('chown root:root %s' % configFile)

        projectConfig['ops_header'] = _503_header

        upload_template('templates/andyet_error.html', '%s/errors/503-error.http' % _cfg_root, 
                    context=projectConfig, use_sudo=True)
        sudo('chown root:root %s/errors/503-error.http' % _cfg_root)

        projectConfig['haproxy.ssl-pem'] = '/etc/haproxy/ssl-keys/%s' % projectConfig['haproxy.pemfile']
        # projectConfig['haproxy.ssl-key'] = '/etc/haproxy/ssl-keys/%s' % projectConfig['haproxy.keyfile']

        put('keys/%s' % projectConfig['haproxy.pemfile'], projectConfig['haproxy.ssl-pem'], use_sudo=True)
        # put('keys/%s' % projectConfig['haproxy.keyfile'], projectConfig['haproxy.ssl-key'], use_sudo=True)

        upload_template('templates/haproxy/haproxy.base', '/etc/haproxy/haproxy.base', context=projectConfig, use_sudo=True)
        sudo('chown root:root /etc/haproxy/haproxy.base')

        put('templates/haproxy/49-haproxy.conf', '/etc/rsyslog.d/49-haproxy.conf', use_sudo=True)
        sudo('chown root:root /etc/rsyslog.d/49-haproxy.conf')
        sudo('service rsyslog restart')

        put('templates/haproxy/build_config.sh', '%s/build_config.sh' % _cfg_root, use_sudo=True)
        sudo('chmod +x %s/build_config.sh' % _cfg_root)

        aclFile  = '%s/haproxy.acls.base' % _cfg_root
        usesFile = '%s/haproxy.uses.base' % _cfg_root

        if not exists(aclFile):
            sudo('touch %s' % aclFile)
        if not exists(usesFile):
            sudo('touch %s' % usesFile)

        if 'haproxy.acls_base' in projectConfig:
            for s in projectConfig['haproxy.acls_base']:
                append(aclFile, s, use_sudo=True)
        if 'haproxy.uses_base' in projectConfig:
            for s in projectConfig['haproxy.uses_base']:
                append(usesFile, s, use_sudo=True)

        if 'haproxy.acls' in projectConfig:
            for s in projectConfig['haproxy.acls']:
                append('%s/%s.acls' % (_site_root, projectConfig['name']), s, use_sudo=True)

        if 'haproxy.uses' in projectConfig:
            for s in projectConfig['haproxy.uses']:
                append('%s/%s.uses' % (_site_root, projectConfig['name']), s, use_sudo=True)

        sudo('/etc/haproxy/build_config.sh')
