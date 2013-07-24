#!/usr/bin/env python

# :copyright: (c) 2013 by &yet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

import os
import json

from fabric.operations import *
from fabric.api import *
from fabric.contrib.files import *
from fabric.colors import *
from fabric.context_managers import cd

import fabops.common
import fabops.redis


@task
def install_blog():
    if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
        if env.host_string in env.apps:
            appname = "andyet-blog"
            appConfig = getAppConfig(appName)

            if isinstance(appConfig, dict) and 'name' in appConfig:
                if appname in env.apps[env.host_string]:
                    fabops.common.install_package('mhddfs')

                    with settings(user=appConfig['deploy_user']):
                        with cd(appConfig['home_dir']):
                            run('wget -O - "https://www.dropbox.com/download?plat=lnx.x86_64" | tar xzf -')

                    put('templates/dropbox_blog.initd', '/etc/init.d/dropbox_blog', use_sudo=True)
                    sudo('chmod +x /etc/init.d/dropbox_blog')
                    sudo('update-rc.d dropbox_blog defaults')
                    sudo('/etc/init.d/dropbox_blog')

                    print("*"*42)
                    print("you need to register the server with dropbox using the link that the service is now spamming")
                    print("you will also need to chmod +r the Dropbox folder so nginx can see it")
                    print("*"*42)

def getProjectConfig(projectName, hostName, itemName=None):
    if itemName is None:
        itemName = projectName
    projectCfgDir = os.path.join(os.path.abspath(env.projectDir), itemName)
    projectCfgFile = os.path.join(projectCfgDir, '%s.cfg' % itemName)
    projectConfig  = {}

    if os.path.exists(projectCfgFile):
        try:
            projectConfig               = json.load(open(projectCfgFile, 'r'))

            projectConfig['name']       = itemName
            projectConfig['configDir']  = projectCfgDir
            projectConfig['configFile'] = projectCfgFile
            projectConfig['homeDir']    = '/home/%s' % projectConfig['deploy_user']
            projectConfig['logDir']     = '/var/log/%s' % itemName

            if 'app_dir' in projectConfig:
                projectConfig['appDir'] = '/home/%s/%s' % (projectConfig['deploy_user'], projectConfig['app_dir'])
            else:
                projectConfig['appDir'] = '/home/%s/%s' % (projectConfig['deploy_user'], itemName)

            if projectName in env.projects and 'qa' in env.projects[projectName]:
                projectConfig['qa'] = env.projects[projectName]['qa']

            defaultConfig = fabops.common.flatten(env.defaults)
            projectConfig = fabops.common.flatten(projectConfig)

            for k in defaultConfig:
                if k not in projectConfig:
                    projectConfig[k] = defaultConfig[k]

            if hostName in env.overrides:
                for k in env.overrides[hostName]:
                    projectConfig[k] = env.overrides[hostName][k]

            if projectConfig['qa']:
                s = 'qa'
            else:
                s = 'prod'
            dnsConfig = fabops.common.flatten(env.dns[s])

            for k in dnsConfig:
                projectConfig['dns.%s' % k] = dnsConfig[k]

        except:
            print('error parsing configuration file %s' % projectCfgFile)
            print(sys.exc_info())
            projectConfig = {}

    return projectConfig

def checkHost(projectName, prod):
    if env.host_string is None:
        hosts   = []
        project = env.projects[projectName]

        if prod:
            hosts = project['hosts']
        else:
            for host in project['hosts']:
                projectConfig = getProjectConfig(projectName, host)
                if projectConfig['qa']:
                    hosts.append(host)
        env.host_string = hosts[0]
        env.hosts.extend(hosts)

def loadProject(projectName, prod):
    if projectName in env.projects:
        checkHost(projectName, prod)

        return getProjectConfig(projectName, env.host_string)
    else:
        return None

@task
def deployProject(projectName, prod=False):
    if projectName in env.projects:
        checkHost(projectName, prod)

        execute('fabops.andyet.deploy', projectName)

@task
def updateProject(projectName, prod=False):
    checkHost(projectName, prod)

    if projectName not in env.projects:
        print('%s not found in list of known projects')
    else:
        if not exists('/etc/andyet_ops_bootstrap'):
            print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
        else:
            if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
                project       = env.projects[projectName]
                projectConfig = getProjectConfig(projectName, env.host_string)

                if 'nginx.sitename' in projectConfig:
                    execute('fabops.nginx.deploy', projectConfig)
                if 'monit.type' in projectConfig:
                    execute('fabops.provision.add_app_to_monit', projectConfig, projectName)
                if 'upstart.type' in projectConfig:
                    execute('fabops.provision.add_app_to_upstart', projectConfig, projectName)
                    if projectConfig['upstart.type'] == 'node':
                        execute('fabops.nodejs.deploy', projectConfig)
                if 'runit.type' in projectConfig:
                    execute('fabops.runit.update_app', projectConfig)
                    if projectConfig['runit.type'] == 'node':
                        execute('fabops.nodejs.deploy', projectConfig)

@task
def deploy(projectName):
    if projectName not in env.projects:
        print('%s not found in list of known projects')
    else:
        if not exists('/etc/andyet_ops_bootstrap'):
            print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
        else:
            if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
                project       = env.projects[projectName]
                projectConfig = getProjectConfig(projectName, env.host_string)

                if 'tasks' in project:
                    for task in project['tasks']:
                        execute('fabops.andyet.deploy_task', projectName, task)

                if 'haproxy.acls' in projectConfig:
                    execute('fabops.haproxy.install_site', projectName, projectConfig)

                if 'deploy_user' in projectConfig:
                    if not fabops.common.user_exists(projectConfig['deploy_user']):
                        fabops.users.adduser(projectConfig['deploy_user'], 'ops.keys')

                    if 'deploy_key' in projectConfig:
                        if fabops.common.user_exists(projectConfig['deploy_user']):
                            fabops.users.adddeploykey(projectConfig['deploy_user'], 
                                                      os.path.join(env.our_path, 'keys', projectConfig['deploy_key']), 
                                                      projectConfig['deploy_key'])
                        if 'repo_keys' in projectConfig:
                            for repoKey in projectConfig['repo_keys']:
                                fabops.users.adddeploykey(projectConfig['deploy_user'], 
                                                          os.path.join(env.our_path, 'keys', repoKey), 
                                                          repoKey)
                        if 'repository_site.key' in projectConfig:
                            fabops.users.adddeploykey(projectConfig['deploy_user'], 
                                                      os.path.join(env.our_path, 'keys', projectConfig['repository_site.key']), 
                                                      projectConfig['repository_site.key'])

                        updateProject(projectName, projectConfig)

@task
def deploy_task(projectName, taskName):
    if not exists('/etc/andyet_ops_bootstrap'):
        print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
    else:
        if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
            if projectName in env.projects and env.host_string in env.projects[projectName]['hosts']:
                projectConfig = getProjectConfig(projectName, env.host_string)
                if taskName in ('nginx', 'redisWeb', 'redisApi', 'errorTests'):
                    execute('fabops.andyet.%s' % taskName, taskName, projectConfig)

@task
def update_app(projectName, appName):
    if not exists('/etc/andyet_ops_bootstrap'):
        print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
    else:
        if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
            if projectName in env.projects and env.host_string in env.projects[projectName]['hosts']:
                projectConfig = getProjectConfig(projectName, env.host_string)
                project       = env.projects[projectName]

                if 'apps' in project and appName in project['apps']:
                    execute('fabops.nodejs.deploy', projectName, projectConfig, force=False)

@task
def opsbot_status(projectName, prod):
    if not exists('/etc/andyet_ops_bootstrap'):
        print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
    else:
        if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
            checkHost(projectName, prod)

            if projectName in env.projects and env.host_string in env.projects[projectName]['hosts']:
                projectConfig = getProjectConfig(projectName, env.host_string)
                project       = env.projects[projectName]

                if 'upstart.type' in projectConfig or 'runit.type' in projectConfig:
                    with settings(user=projectConfig['deploy_user'], use_sudo=True):
                        if exists(projectConfig['deploy_dir']):
                            with cd(projectConfig['deploy_dir']):
                                run('git status')
                        else:
                            print('project is not deployed')

@task
def opsbot_deploy(projectName, prod):
    if not exists('/etc/andyet_ops_bootstrap'):
        print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
    else:
        updateProject(projectName, prod)

@task
def opsbot_service(projectName, prod, state):
    if not exists('/etc/andyet_ops_bootstrap'):
        print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
    else:
        if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
            checkHost(projectName, prod)

            if projectName in env.projects and env.host_string in env.projects[projectName]['hosts']:
                projectConfig = getProjectConfig(projectName, env.host_string)
                project       = env.projects[projectName]

                if 'upstart.type' in projectConfig:
                    sudo('service %s %s' % (projectName, state))
                else:
                    sudo('sv %s %s' % (state, projectName))

@task
def opsbot_start(projectName, prod):
    execute('fabops.andyet.opsbot_service', projectName, prod, 'start')

@task
def opsbot_stop(projectName, prod):
    execute('fabops.andyet.opsbot_service', projectName, prod, 'stop')

@task
def enable_runit(projectName):
    projectConfig = loadProject(projectName)
    execute('fabops.runit.enable_app', projectConfig)

@task
def disable_runit(projectName):
    projectConfig = loadProject(projectName)
    execute('fabops.runit.disable_app', projectConfig)

@task
def errorTests(taskName, projectConfig):
    if not exists('/srv/andyet_errors'):
        sudo('mkdir -p /srv/andyet_errors/500')
    upload_template('templates/andyet_error.html', '/srv/andyet_errors/500/andyet_error.html',
                    context=projectConfig, use_sudo=True)
    sudo('chown -R root:root /srv/andyet_errors')

@task
def nginx(taskName, projectConfig):
    execute('fabops.nginx.install')

@task
def redisWeb(taskName, projectConfig):
    fabops.redis.deploy(taskName, projectConfig)

@task
def redisApi(taskName, projectConfig):
    fabops.redis.deploy(taskName, projectConfig)

@task
def riak(taskName, projectConfig):
    fabops.riak.deploy(taskName, projectConfig)
