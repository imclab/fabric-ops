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

_version  = '1.2.6'
_tarball  = 'nginx-%s.tar.gz' % _version
_url      = 'http://nginx.org/download/%s' % _tarball
_tmp_dir  = '/tmp/nginx-%s' % _version
_username = 'nginx'

@task
def download():
    """
    Download and extract the nginx tarball
    """
    with cd('/tmp'):
        run('wget %s' % _url)
        run('tar xf %s' % _tarball)

@task
def build():
    """
    Run ./configure for nginx and then make
    """
    if exists(_tmp_dir):
        with cd(_tmp_dir):
            run('./configure --conf-path=/etc/nginx/nginx.conf --pid-path=/var/run/nginx.pid --user=nginx --with-http_stub_status_module')
            run('make')

@task
def install(force=False):
    """
    Install nginx
    Download, extract, configure and install nginx if the nginx
    user does not already exist.

    Force install by calling as nginx.install:true
    """
    if not force and fabops.common.user_exists(_username):
        print('nginx user already exists, skipping nginx install')
    else:
        for p in ('build-essential', 'libpcre3-dev', 'zlib1g-dev'):
            fabops.common.install_package(p)

        download()
        build()
        if exists(_tmp_dir):
            sudo('useradd --system %s' % _username)
            with cd(_tmp_dir):
                sudo('make install')
                sudo('ln -s /usr/local/nginx/sbin/nginx /usr/local/sbin/nginx')
        put('templates/nginx/nginx_initd_script', '/etc/init.d/nginx', use_sudo=True)
        sudo('chmod +x /etc/init.d/nginx')

    upload_template('templates/nginx/nginx.conf', '/etc/nginx/nginx.conf', 
                    context=env.nginx,
                    use_sudo=True)
    sudo('chown root:root /etc/nginx/nginx.conf')

    if not exists('/var/log/nginx'):
        sudo('mkdir /var/log/nginx')

    for p in ['ops-common', 'conf.d']:
        if not exists('/etc/nginx/%s' % p):
            sudo('mkdir /etc/nginx/%s' % p)

    for f in fabops.common.list_files('templates/nginx/ops-common'):
        upload_template(os.path.join('templates/nginx/ops-common', f), '/etc/nginx/ops-common',
                        context=env.nginx,
                        use_sudo=True)
        sudo('chown root:root /etc/nginx/ops-common/%s' % f)

@task
def install_site(siteName, siteConfig):
    if not exists('/etc/nginx'):
        install()

    if exists('/etc/nginx'):
        cfg = fabops.common.flatten(siteConfig)

        if 'nginx.root' not in cfg:
            print('nginx.root not found in site configuration')
        s = ''
        if 'nginx.listen' in cfg:
            s = cfg['nginx.listen']
        if 'nginx.port' in cfg:
            if len(s) > 0:
                s += ':'
            s += str(cfg['nginx.port'])
        cfg['nginx.listen'] = s

        upload_template(os.path.join(siteConfig['site_config_dir'], '%s.nginx' % cfg['name']),
                        '/etc/nginx/conf.d/%s' % cfg['name'],
                        context=cfg,
                        use_sudo=True)
        sudo('chown root:root /etc/nginx/conf.d/%s' % cfg['name'])
        sudo('mkdir -p %s' % cfg['nginx.root'])
        sudo('chown nginx:nginx %s' % cfg['nginx.root'])

@task
def deploy_site(siteConfig):
    """
    Deploy an installed nginx site
    """
    if fabops.common.user_exists(siteConfig['deploy_user']):
        with settings(user=siteConfig['deploy_user'], key_filename='/home/%s/.ssh/%s' % (siteConfig['deploy_user'], siteConfig['deploy_key'])):
            tempDir = '/tmp/%s' % siteConfig['name']
            workDir = os.path.join(tempDir, siteConfig['name'])

            if exists(workDir):
                run('rm -rf %s' % workDir)
            else:
                run('mkdir -p %s' % workDir)
            
            run('git clone %s %s' % (siteConfig['repository']['url'], workDir))

            with cd(workDir):
                run('git checkout %s' % siteConfig['deploy_branch'])
                sudo('cp %s/* %s' % (workDir, siteConfig['nginx']['root']))
        if sudo('service nginx testconfig'):
            sudo('service nginx restart')
