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

_version   = '1.5.1'
_tarball   = 'nginx-%s.tar.gz' % _version
_url       = 'http://nginx.org/download/%s' % _tarball
_tmp_dir   = '/tmp/nginx-%s' % _version
_username  = 'nginx'
_configure = ' '.join(['--prefix=/usr/local/nginx',
                       '--conf-path=/etc/nginx/nginx.conf',
                       '--pid-path=/var/run/nginx.pid',
                       '--user=%s' % _username,
                       '--with-http_stub_status_module',
                       '--with-http_ssl_module',
                      ])
@task
def download():
    """
    Download and extract the nginx tarball
    """
    with cd('/tmp'):
        if exists(_tarball):
            run('rm -f %s' % _tarball)
        run('wget %s' % _url)
        run('tar xf %s' % _tarball)

@task
def build():
    """
    Run ./configure for nginx and then make
    """
    if exists(_tmp_dir):
        with cd(_tmp_dir):
            run('./configure %s' % _configure)
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
        for p in ('build-essential', 'libssl-dev', 'libpcre3-dev', 'zlib1g-dev'):
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
        sudo('update-rc.d nginx defaults')

    upload_template('templates/nginx/nginx.conf', '/etc/nginx/nginx.conf', 
                    context=env.defaults['nginx'],
                    use_sudo=True)
    sudo('chown root:root /etc/nginx/nginx.conf')

    if not exists('/var/log/nginx'):
        sudo('mkdir /var/log/nginx')

    for p in ['ops-common', 'conf.d', 'ssl-keys']:
        if not exists('/etc/nginx/%s' % p):
            sudo('mkdir /etc/nginx/%s' % p)

    for f in fabops.common.list_files('templates/nginx/ops-common'):
        upload_template(os.path.join('templates/nginx/ops-common', f), '/etc/nginx/ops-common',
                        context=env.defaults['nginx'],
                        use_sudo=True)
        sudo('chown root:root /etc/nginx/ops-common/%s' % f)

@task
def deploy(projectConfig):
    """
    Deploy a project's website configuration with nginx

    assumes deploy user is already enabled
    """
    if not fabops.common.user_exists(_username):
        install()

    nginxConfig = '/etc/nginx/conf.d/%s.conf' % projectConfig['name']

    upload_template(os.path.join(projectConfig['configDir'], '%s.nginx' % projectConfig['name']),
                    nginxConfig,
                    context=projectConfig,
                    use_sudo=True)
    sudo('chown root:root %s' % nginxConfig)

    if 'nginx.ssl_cert' in projectConfig:
        put(os.path.join(env.our_path, 'keys', projectConfig['nginx.ssl_cert']), 
            '/etc/nginx/ssl-keys/%s' % projectConfig['nginx.ssl_cert'], use_sudo=True)
    if 'nginx.ssl_cert_key' in projectConfig:
        put(os.path.join(env.our_path, 'keys', projectConfig['nginx.ssl_cert_key']), 
            '/etc/nginx/ssl-keys/%s' % projectConfig['nginx.ssl_cert_key'], use_sudo=True)

    if 'repository_site.type' in projectConfig:
        repoUrl      = projectConfig['repository_site.url']
        tempDir      = os.path.join('/home', projectConfig['deploy_user'], 'work')
        workDir      = os.path.join(tempDir, projectConfig['name'])
        if 'repository_site.alias' in projectConfig:
            targetDir = os.path.join('/home', projectConfig['deploy_user'], projectConfig['repository_site.alias'])
        else:
            targetDir = os.path.join('/home', projectConfig['deploy_user'], projectConfig['name'])
        if 'repository_site.key' in projectConfig:
            siteKey = projectConfig['repository_site.key']
        else:
            siteKey = projectConfig['deploy_key']
        if 'repository_site.branch' in projectConfig:
            deployBranch = projectConfig['repository_site.branch']
        else:
            deployBranch = projectConfig['deploy_branch']

        if exists(tempDir):
            sudo('rm -rf %s' % tempDir)

        with settings(user=projectConfig['deploy_user']):
            run('mkdir -p %s' % targetDir)
            run('mkdir -p %s' % workDir)

            run('ssh-add -D; ssh-add .ssh/%s' % siteKey)
            run('git clone %s %s' % (repoUrl, workDir))

            with cd(workDir):
                if run('git checkout %s' % deployBranch):
                    run('cp -r %s/* %s' % (workDir, targetDir))

            upload_template('templates/project_deploy.sh', 'deploy.sh', context=projectConfig)
            run('chmod +x %s' % os.path.join(projectConfig['homeDir'], 'deploy.sh'))
    else:
        print('site does not have a defined site repository, skipping')

    if sudo('service nginx testconfig'):
        sudo('service nginx restart')
