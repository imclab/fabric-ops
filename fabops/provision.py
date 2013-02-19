#!/usr/bin/env python

import os
import json
import shutil

# :copyright: (c) 2013 by AndYet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

from fabric.operations import *
from fabric.api import *
from fabric.contrib.files import *
from fabric.colors import *
from fabric.context_managers import cd

import fabops.common
import fabops.users


def getAppConfig(appName):
    appDir     = os.path.join(os.path.abspath(env.app_dir), appName)
    appCfgFile = os.path.join(appDir, '%s.cfg' % appName)

    print appCfgFile
    if os.path.exists(appCfgFile):
        try:
            appConfig = json.load(open(appCfgFile, 'r'))
        except:
            print('error parsing configuration file %s' % appCfgFile)
            print(sys.exc_info())
            appConfig = {}

    appConfig['app_dir']    = appDir
    appConfig['app_config'] = appCfgFile

    if 'deploy_user' not in appConfig:
        appConfig['deploy_user'] = appConfig['name']

    appConfig['home_dir'] = '/home/%s' % appConfig['deploy_user']
    appConfig['app_dir']  = os.path.join(appConfig['home_dir'], appConfig['name'])

    return appConfig

def getAppDetails(appConfig):
    result = False

    if 'repository' in appConfig and appConfig['repository']['type'] == 'git':
        appName     = appConfig['name']
        gitRepoUrl  = appConfig['repository']['url']
        tempDir     = os.environ['TMPDIR']
        tempRepoDir = os.path.join(tempDir, appName)
    
        appConfig['app_details'] = { 'tempRepoDir': tempRepoDir,
                                     'language':    None,
                                   }

        # TODO need to make this work with the app's deploy key
        with cd(tempDir):
            if os.path.exists(tempRepoDir):
                shutil.rmtree(tempRepoDir)
            local('git clone %s %s' % (gitRepoUrl, tempRepoDir))

        if os.path.exists(tempRepoDir):
            packageFile = '%s/package.json' % tempRepoDir

            if os.path.exists(packageFile):
                appConfig['app_details']['language'] = 'node'
                try:
                    appConfig['app_details']['package'] = json.load(open(packageFile, 'r'))
                    result = True
                except:
                    print('error loading the package.json file %s' % packageFile)
                    print(sys.exc_info())
                    appConfig['app_details']['package'] = {}
            else:
                result = True
        else:
            print('unable to checkout repo for %s [%s]' % (appName, gitRepoUrl))
    else:
        print('currently only apps from git repos can be handled - skipping app install')

    return result

@task
def app_install(appName=None):
    if appName is None:
        print('no appName given, nothing to do')
    else:
        appConfig = getAppConfig(appName)

        if not fabops.common.user_exists(appConfig['deploy_user']):
            fabops.users.adduser(appConfig['deploy_user'], 'ops.keys')

        if fabops.common.user_exists(appConfig['deploy_user']):
            fabops.users.addprivatekey(appConfig['deploy_user'], os.path.join(env.our_path, 'keys', appConfig['deploy_key']))

        if 'nginx' in appConfig:
            for siteConfig in appConfig['nginx']:
                fabops.nginx.site(siteConfig, appConfig)

        if 'upstart' in appConfig:
            upstart(appConfig)

        if isinstance(appConfig, dict) and 'name' in appConfig:
            if getAppDetails(appConfig):
                if appConfig['app_details']['language'] == 'node':
                    fabops.nodejs.install_app(appConfig)
        else:
            print('Unable to find (or load) the configuration file for %s in %s [%s]' % (appName, appConfig['app_dir'], appConfig['app_config']))

@task
def app_install_all():
    for d in fabops.list_dirs(env.app_dir):
        app_install(d)

@task
def monit(appConfig):
    d = { 'name':        appConfig['name'],
          'user':        appConfig['deploy_user'],
          'appdir':      appConfig['app_dir'],
          'description': appconfig['description'],
          'piddir':      '/var/run/%s/' % appConfig['name'],
          'pidfile':     '%s.pid'       % appConfig['name'],
          'logdir':      '/var/log/%s/' % appConfig['name'],
          'logfile':     '%s.log'       % appConfig['name'],
          'start':       appConfig['monit']['start'],
          'stop':        appConfig['monit']['stop'],
          'alerts':      '',
        }

    if 'alerts' in appConfig['monit']:
        for t in appConfig['monit']['alerts']:
            d['alerts'] += '%s\n' % t

    if not exists('/etc/monit/conf.d'):
        fabops.common.install_package('monit')

    upload_template('templates/monit/%s.conf' % appConfig['monit']['type'],
                    '/etc/monit/conf.d/%s.conf' % appConfig['name'],
                    context=d,
                    use_sudo=True)

@task
def upstart(appConfig):
    d = { 'name':        appConfig['name'],
          'user':        appConfig['deploy_user'],
          'appdir':      appConfig['app_dir'],
          'description': appConfig['description'],
          'piddir':      '/var/run/%s/' % appConfig['name'],
          'pidfile':     '%s.pid'       % appConfig['name'],
          'logdir':      '/var/log/%s/' % appConfig['name'],
          'logfile':     '%s.log'       % appConfig['name'],
        }

    upload_template('templates/node_upstart_script', '/etc/init/%s.conf' % appConfig['name'], 
                    context=d,
                    use_sudo=True)
    if not exists(d['piddir']):
        sudo('mkdir %(piddir)s' % d)
    if not exists(d['logdir']):
        sudo('mkdir %(logdir)s' % d)

    sudo('chown %(user)s:%(user)s %(piddir)s' % d)
    sudo('chown %(user)s:%(user)s %(logdir)s' % d)

@task
def upgrade():
    """
    Update the apt cache and perform an upgrade
    """
    if sudo('DEBIAN_FRONTEND=noninteractive apt-get update').failed:
        abort()
    if sudo('DEBIAN_FRONTEND=noninteractive apt-get upgrade -y').failed:
        abort()
    if sudo('DEBIAN_FRONTEND=noninteractive apt-get autoremove -y').failed:
        abort()

@task
def disableroot():
    """
    Set PermitRootLogin in sshd_config to false
    """
    sed('/etc/ssh/sshd_config', 'PermitRootLogin\syes', 'PermitRootLogin no', use_sudo=True)

@task
def disablepasswordauth():
    """
    Uncomment PasswordAuthentication and set it to no
    """
    uncomment('/etc/ssh/sshd_config', 'PasswordAuthentication\syes', use_sudo=True)
    sed('/etc/ssh/sshd_config', 'PasswordAuthentication\syes', 'PasswordAuthentication no', use_sudo=True)

@task
def disablex11():
    """
    Set X11Forwarding to no
    """
    sed('/etc/ssh/sshd_config', 'X11Forwarding\syes', 'X11Forwarding no', use_sudo=True)

@task
def create_instance():
    """
    Create and setup an empty server
    """
    pass

@task(default=True)
def bootstrap(user=None):
    """
    Bootstrap a single given server
    The server is checked for upgrades and the ops user is
    installed so that fabric can be used going forward
    """
    if user is None:
        user = 'root'

    print('-'*42)
    print('Bootstrapping OS for a single host.  Fabric user is being forced to "%s".' % user)
    print('NOTE: be aware you may be prompted for a sudo password...')
    print('-'*42)

    with settings(user=user):
        fabops.users.adduser('ops', 'ops.keys', True)

        append('/etc/sudoers', '%ops    ALL=(ALL:ALL) NOPASSWD: ALL\n', use_sudo=True)

        upgrade()
        disablex11()
        for p in ('ntp', 'fail2ban', 'screen', 'build-essential', 'git'):
            fabops.common.install_package(p)

    # TODO enable these after we are *sure* things are working with SSH for ops user
    # disableroot()
    # disablepasswordauth()

@task
def configure():
    """
    Configure the server with the baseline packages
    """
    # for p in ('build-essential', 'git'):
    #     fabops.install_package(p)
    pass