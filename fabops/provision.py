#!/usr/bin/env python

# :copyright: (c) 2013 by &yet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

import os
import json
import shutil
import socket

from fabric.operations import *
from fabric.api import *
from fabric.contrib.files import *
from fabric.colors import *
from fabric.context_managers import cd

import fabops.common
import fabops.users


def getIPAddress(hostname):
    return socket.gethostbyname(hostname)

@task
def devtools(python=False):
    for p in ('build-essential', 'git', 'python-virtualenv'):
        fabops.common.install_package(p)

    if python:
        fabops.common.install_package('python-dev')

def getSiteConfig(siteName, qa=False):
    siteCfgDir  = os.path.join(os.path.abspath(env.site_dir), siteName)
    siteCfgFile = os.path.join(siteCfgDir, '%s.cfg' % siteName)

    if os.path.exists(siteCfgFile):
        try:
            siteConfig = json.load(open(siteCfgFile, 'r'))
        except:
            print('error parsing configuration file %s' % siteCfgFile)
            print(sys.exc_info())
            siteConfig = {}

    siteConfig['qa']              = qa
    siteConfig['site_config_dir'] = siteCfgDir
    siteConfig['site_config']     = siteCfgFile

    return siteConfig

def getAppConfig(appName, qa=False):
    appCfgDir  = os.path.join(os.path.abspath(env.app_dir), appName)
    appCfgFile = os.path.join(appCfgDir, '%s.cfg' % appName)

    if os.path.exists(appCfgFile):
        try:
            appConfig = json.load(open(appCfgFile, 'r'))
        except:
            print('error parsing configuration file %s' % appCfgFile)
            print(sys.exc_info())
            appConfig = {}

    appConfig['qa']             = qa
    appConfig['app_config_dir'] = appCfgDir
    appConfig['app_config']     = appCfgFile

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

    return result

@task
def site_install(siteName=None, qa=False):
    if siteName is None:
        print('no siteName given, nothing to do')
    else:
        siteConfig = getSiteConfig(siteName, qa=qa)

        print('site_install for %s' % siteName)
        print(siteConfig)

        if 'deploy_user' in siteConfig:
            print('deploy_user setup')
            if not fabops.common.user_exists(siteConfig['deploy_user']):
                fabops.users.adduser(siteConfig['deploy_user'], 'ops.keys')

            if 'deploy_key' in siteConfig:
                if fabops.common.user_exists(siteConfig['deploy_user']):
                    fabops.users.adddeploykey(siteConfig['deploy_user'], 
                                              os.path.join(env.our_path, 'keys', siteConfig['deploy_key']), 
                                              siteConfig['deploy_key'])

        if 'haproxy' in siteConfig:
            execute('fabops.haproxy.install_site', siteName, siteConfig)

        if 'nginx' in siteConfig:
            execute('fabops.nginx.install_site', siteName, siteConfig)

            execute('fabops.nginx.deploy_site', siteConfig)

@task
def site_deploy(siteName=None):
    if siteName is None:
        print('no siteName given, nothing to do')
    else:
        siteConfig = getSiteConfig(siteName)

        if 'nginx' in siteConfig and fabops.common.user_exists(siteConfig['deploy_user']):
            fabops.nginx.deploy_site(siteConfig)

@task
def app_install(appName=None, qa=False):
    if appName is None:
        print('no appName given, nothing to do')
    else:
        appConfig = getAppConfig(appName, qa=qa)

        if not fabops.common.user_exists(appConfig['deploy_user']):
            fabops.users.adduser(appConfig['deploy_user'], 'ops.keys')

        if 'deploy_key' in appConfig and fabops.common.user_exists(appConfig['deploy_user']):
            fabops.users.adddeploykey(appConfig['deploy_user'], 
                                      os.path.join(env.our_path, 'keys', appConfig['deploy_key']), 
                                      appConfig['deploy_key'])

        if getAppDetails(appConfig):
            if 'upstart' in appConfig:
                add_app_to_upstart(appConfig)

            add_app_to_monit(appConfig)

            if isinstance(appConfig, dict) and 'name' in appConfig:
                if appConfig['app_details']['language'] == 'node':
                    fabops.nodejs.install_app(appConfig)
        else:
            print('Unable to find (or load) the configuration file for %s in %s' % (appName, appConfig['app_config_dir']))

@task
def app_deploy(appName=None):
    if appName is None:
        print('no appName given, nothing to do')
    else:
        appConfig = getAppConfig(appName)

        if isinstance(appConfig, dict) and 'name' in appConfig:
            if fabops.common.user_exists(appConfig['deploy_user']) and getAppDetails(appConfig):
                if appConfig['app_details']['language'] == 'node':
                    fabops.nodejs.deploy_app(appConfig)
        else:
            print('Unable to find (or load) the configuration file for %s in %s' % (appName, appConfig['app_config_dir']))

@task
def alerts():
    if not exists('/opt/sbin'):
        sudo('mkdir -p /opt/sbin')
    if not exists('/opt/sbin/alert_email.sh'):
        upload_template('templates/alerts/alert_email.sh', '/opt/sbin/alert_email.sh', use_sudo=True)
        sudo('chmod +x /opt/sbin/alert_email.sh')
    if not exists('/opt/sbin/alert_email.py'):
        sudo('pip install requests')
        sudo('pip install sleekxmpp')
        upload_template('templates/alerts/alert_email.py', '/opt/sbin/alert_email.py', use_sudo=True)
        sudo('chmod +x /opt/sbin/alert_email.py')

    for s in ('alerts: alert', 'alert: root', 'root: | "/opt/sbin/alert_email.sh"'):
        if not contains('/etc/aliases', s, use_sudo=True):
            append('/etc/aliases', s, use_sudo=True)

@task
def add_app_to_monit(appConfig):
    d = { 'name':        appConfig['name'],
          'user':        appConfig['deploy_user'],
          'appdir':      appConfig['app_dir'],
          'description': appConfig['description'],
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

    upload_template('templates/monit/%s.conf' % appConfig['monit']['type'],
                    '/etc/monit/conf.d/%s.conf' % appConfig['name'],
                    context=d,
                    use_sudo=True)

@task
def add_app_to_upstart(appConfig):
    packageJson = appConfig['app_details']['package']

    if 'scripts' in packageJson and "start" in packageJson['scripts']:
        appstart = packageJson['scripts']['start']
    else:
        appstart = 'node server'

    d = { 'name':        appConfig['name'],
          'user':        appConfig['deploy_user'],
          'appdir':      appConfig['app_dir'],
          'description': appConfig['description'],
          'appstart':    appstart,
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

@task()
def pin_packages():
    for p in env.pinned:
        sudo('echo %s hold | dpkg --set-selections' % p)

@task
def apt_update(quiet=True):
    """
    run apt-get update
    """
    opts = "-qq" if quiet else ""
    sudo("apt-get update %s" % opts)

@task
def apt_upgrade(quiet=True):
    """
    Update the apt cache and perform an upgrade
    """
    opts = "-qq" if quiet else ""
    sudo('DEBIAN_FRONTEND=noninteractive apt-get upgrade -y %s' % opts)

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

@task
def install_postfix(mailname='localhost'):
    if not fabops.common.is_installed('postfix'):
        fabops.common.preseed_package('postfix', {
            'postfix/main_mailer_type': ('select', 'Internet Site'),
            'postfix/mailname': ('string', mailname),
            'postfix/destinations': ('string', '%s, localhost.localdomain, localhost ' % mailname),
        })
        fabops.common.install_package('postfix')

@task
def install_monit():
    if not fabops.common.is_installed('monit'):
        fabops.common.install_package('monit')
        put('templates/monit/monitrc', '/etc/monit/monitrc', use_sudo=True)
    sudo('chown root:root /etc/monit/monitrc')
    sudo('chmod 0600 /etc/monit/monitrc')

@task
def install_munin_node():
    if not fabops.common.is_installed('munin-node'):
        fabops.common.install_package('munin-node')

    put('templates/munin/munin-node.conf', '/etc/munin/munin-node.conf', use_sudo=True)
    put('templates/munin/munin-node_plugins.conf', '/etc/munin/plugin-conf.d/munin-node', use_sudo=True)        
    sed('/etc/munin/munin-node.conf', 'host_name localhost', 'host_name %s' % env.host_string, use_sudo=True)

    sudo('chown root:root /etc/munin/munin-node.conf')

@task
def set_hostname():
    """
    Set the hostname for a server
    """
    sudo('echo %s > /etc/hostname' % env.host_string)
    sudo('/etc/init.d/hostname start')
    sed('/etc/hosts', '127.0.0.1\slocalhost', '127.0.0.1 localhost %s' % env.host_string, use_sudo=True)

@task
def enable_iptables():
    # TODO need to add saving of /etc/iptables.rules
    # TODO need to add /etc/network/if-pre-up.d/iptables:
    #                   #!/bin/sh
    #                   iptables-restore < /etc/iptables.rules
    #                   exit 0
    # TODO chmod +x /etc/network/if-pre-up.d/iptables

    upload_template('templates/iptables/iptables.sh', '/root/iptables.sh', use_sudo=True)
    sudo('chmod +x /root/iptables.sh')

    ips = []
    # loop thru app servers and add them if we are a storage server
    append('/root/iptables.sh', '# Add IP exceptions for our known list of application servers', use_sudo=True)
    if env.host_string in env.roledefs['redis_api']:
        for h in env.roledefs['app']:
            ip = getIPAddress(h)
            if ip not in ips:
                ips.append(ip)
    if env.host_string in env.roledefs['riak']:
        for h in env.roledefs['app']:
            ip = getIPAddress(h)
            if ip not in ips:
                ips.append(ip)

    for ip in ips:
        append('/root/iptables.sh', 'iptables -A INPUT  -p tcp --dport 6379 -s %s/32 -m state --state NEW,ESTABLISHED -j ACCEPT' % ip, use_sudo=True)
        append('/root/iptables.sh', 'iptables -A INPUT  -p tcp --dport 8087 -s %s/32 -m state --state NEW,ESTABLISHED -j ACCEPT' % ip, use_sudo=True)

    append('/root/iptables.sh', 'iptables -A OUTPUT -p tcp --sport 6379 -m state --state ESTABLISHED -j ACCEPT', use_sudo=True)
    append('/root/iptables.sh', 'iptables -A OUTPUT -p tcp --sport 8087 -m state --state ESTABLISHED -j ACCEPT', use_sudo=True)

@task()
def add_ops_user(user=None):
    if user is None:
        user = 'root'

    with settings(user=user):
        if not fabops.common.user_exists('ops'):
            fabops.users.adduser('ops', 'ops.keys', True)
            append('/etc/sudoers', '%ops    ALL=(ALL:ALL) NOPASSWD: ALL\n', use_sudo=True)

@task()
def baseline(user=None):
    """
    Update a new instance created from a stock Ubuntu image
    The server is checked for upgrades and the ops user is
    installed so that fabric can be used going forward
    """
    with settings(user='root'):
        add_ops_user(user)

        apt_update()
        apt_upgrade()
        disablex11()
        
        for p in ('ntp', 'fail2ban', 'screen',):
            fabops.common.install_package(p)

        disableroot()
        disablepasswordauth()
        enable_iptables()
        devtools()
        alerts()
        install_monit()


@task()
def bootstrap(user=None):
    """
    Bootstrap a single given server from our baseline image
    The server is checked for upgrades and the ops user is
    installed so that fabric can be used going forward
    """
    if user is None:
        user = 'ops'

    print('-'*42)
    print('Bootstrapping OS for a single host.  Fabric user is "%s".' % user)
    print('NOTE: be aware you may be prompted for a sudo password...')
    print('-'*42)

    with settings(user=user):
        add_ops_user(user)

        apt_update()
        apt_upgrade()
        disablex11()
        
        # moved into baseline image
        #for p in ('ntp', 'fail2ban', 'screen',):
        #    fabops.common.install_package(p)

        disableroot()
        disablepasswordauth()
        set_hostname()
        enable_iptables()
        devtools()
        alerts()
        install_monit()

        sudo('touch /etc/andyet_ops_bootstrap')
