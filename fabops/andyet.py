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
import fabops.nodejs


@task
def install_ngrok():
    if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
        if not fabops.common.user_exists('ngrokd'):
            fabops.users.adduser('ngrokd', 'ops.keys')

        for p in ('mercurial', 'bzr'):
            fabops.common.install_package(p)
        # wget https://godeb.s3.amazonaws.com/godeb-amd64.tar.gz
        # tar xf godeb-amd64.tar.gz
        # ./godeb install 1.1.2

        with settings(user='ngrokd', use_sudo=True):
            if exists('/home/ngrokd/ngrok'):
                run('rm -rf /home/ngrokd/ngrok')

            run('git clone https://github.com/inconshreveable/ngrok.git')
            run('cd ngrok && make')

@task
def install_kenkou():
    if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
        if not fabops.common.user_exists('kenkou'):
            fabops.users.adduser('kenkou', 'ops.keys')

        with settings(user='kenkou', use_sudo=True):
            run('virtualenv kenkou')
            run('cd kenkou; . bin/activate; pip install https://github.com/bear/bearlib.git; pip install requests')
            run('cd kenkou; . bin/activate; git clone https://github.com/bear/kenkou.git')

@task
def install_reports():
    if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
        projectConfig = getProjectConfig('reports', 'reports')

        if not fabops.common.user_exists('reports'):
            fabops.users.adduser('reports', 'ops.keys')

        with settings(user='reports', use_sudo=True):
            if not exists('/home/reports/.nvm'):
                fabops.nodejs.install_Node('reports', projectConfig['node'], '/home/reports/')

            with cd('/home/reports/'):
                run('. /home/reports/.nvm/nvm.sh; npm install -g plato')

_report_link = """
<p><a href="%(name)s_%(branch)s/plato/index.html">%(name)s %(branch)s</a></p>
"""
_update_bash_script = """#!/bin/bash

"""
@task
def run_reports():
    if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
        projectConfig = getProjectConfig('reports', 'reports')

        s = ''
        for p in env.reports:
            r = env.reports[p]
            r['name'] = p
            s += _report_link % r
            if not exists('/home/reports/.ssh/%s' % r['key']):
                fabops.users.adddeploykey('reports', 
                                          os.path.join(env.our_path, 'keys', r['key']), 
                                          r['key'])

        projectConfig['reports_links'] = s

        if 'nginx.sitename' in projectConfig:
            execute('fabops.nginx.deploy', projectConfig)

        with settings(user='reports', use_sudo=True):
            upload_template('templates/reports_index.html', 'index.html', context=projectConfig)
            s = _update_bash_script
            for p in env.reports:
                r = env.reports[p]
                if not exists('/home/reports/%s_%s' % (p, r['branch'])):
                    run('mkdir -p /home/reports/%s_%s/plato' % (p, r['branch']))
                s += 'echo "processing %s %s"\n' % (p, r['branch'])
                s += 'cd /home/reports/%s_%s\n' % (p, r['branch'])
                s += 'ssh-add -D; ssh-add ~/.ssh/%s\n' % r['key']
                s += 'rm -rf /home/reports/%s_%s/%s\n' % (p, r['branch'], p)
                s += 'git clone %s\n' % r['repo']
                s += 'cd /home/reports/%s_%s/%s\n' % (p, r['branch'], p)
                s += 'git pull origin %s\n' % r['branch']
                s += 'git checkout %s\n' % r['branch']
                s += 'REPORT_PATH=/home/reports/%s_%s/plato ./scripts/reports.sh\n' % (p, r['branch'])
                s += '\n'
            append('/home/reports/update.sh', s)
            run('chmod +x /home/reports/update.sh')

@task
def install_kochiku(force=False):
    if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
        cfg = getProjectConfig('kochiku', 'prod', 'ops')

        execute('fabops.kochiku.install', cfg, force)

@task
def install_logstash(force=False):
    if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
        cfg = getProjectConfig('logs', 'prod', 'ops')

        execute('fabops.logstash.install', cfg, force)

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

def getProjectConfig(projectName, ci, hostName, itemName=None):
    if itemName is None:
        itemName = projectName
    projectCfgDir  = os.path.join(os.path.abspath(env.projectDir), itemName)
    projectCfgFile = os.path.join(projectCfgDir, '%s.cfg' % itemName)
    projectConfig  = {}

    if os.path.exists(projectCfgFile):
        projectConfig               = json.load(open(projectCfgFile, 'r'))
        projectConfig['name']       = itemName
        projectConfig['configDir']  = projectCfgDir
        projectConfig['configFile'] = projectCfgFile
        projectConfig['ci']         = ci
        projectConfig['hostname']   = hostName

        if 'deploy_user' in projectConfig:
            projectConfig['homeDir'] = '/home/%s' % projectConfig['deploy_user']
            projectConfig['logDir']  = '/var/log/%s' % itemName

            if 'deploy_dir' not in projectConfig:
                projectConfig['deploy_dir'] = itemName

            if 'app_dir' in projectConfig:
                projectConfig['appDir'] = '/home/%s/%s' % (projectConfig['deploy_user'], projectConfig['app_dir'])
            else:
                projectConfig['app_dir'] = itemName
                projectConfig['appDir'] =  '/home/%s/%s' % (projectConfig['deploy_user'], itemName)

        defaultConfig = fabops.common.flatten(env.defaults)
        projectConfig = fabops.common.flatten(projectConfig)

        for k in defaultConfig:
            if k not in projectConfig:
                projectConfig[k] = defaultConfig[k]

        dnsConfig = fabops.common.flatten(env.dns[projectConfig['ci']])
        for k in dnsConfig:
            projectConfig['dns.%s' % k] = dnsConfig[k]

        andyetConfig = fabops.common.flatten(env.andyet[projectConfig['ci']])
        for k in andyetConfig:
            projectConfig['andyet.%s' % k] = andyetConfig[k]

        if 'deploy_branch' not in projectConfig:
            if projectConfig['ci'] == 'beta':
                projectConfig['deploy_branch'] = 'beta'
            else:
                projectConfig['deploy_branch'] = 'master'

        if hostName in env.overrides:
            for k in env.overrides[hostName]:
                projectConfig[k] = env.overrides[hostName][k]

        if itemName in env.overrides['ci_project'] and ci in env.overrides['ci_project'][itemName]:
            for k in env.overrides['ci_project'][itemName][ci]:
                projectConfig[k] = env.overrides['ci_project'][itemName][ci][k]

    return projectConfig

def checkHost(projectName, ci):
    if env.host_string is None:
        hosts   = []
        project = env.projects[projectName]

        for host in project['hosts']:
            projectConfig = getProjectConfig(projectName, ci, host)
            if projectConfig['ci'] == ci:
                hosts.append(host)

        env.host_string = hosts[0]
        env.hosts.extend(hosts)

        print 'generating', ci, 'environment for', env.hosts

def loadProject(projectName, ci):
    if projectName in env.projects:
        checkHost(projectName, ci)
        return getProjectConfig(projectName, ci, env.host_string)
    else:
        return None

@task
def deployProject(projectName, ci):
    if projectName in env.projects:
        checkHost(projectName, ci)
        execute('fabops.andyet.deploy', projectName, ci)

_logstash_bucker = """
        file {
                type => "console"
                path => ["/var/log/%s/current"]
                exclude => ["*.gz"]
                sincedb_path => "/opt/logstash"
                debug => true
        }
"""
_logstash_nginx = """
        file {
                type => "nginx_access"
                path => ["/var/log/nginx/%s_access.log"]
                exclude => ["*.gz"]
                format => "json_event"
                sincedb_path => "/opt/logstash"
                debug => true
                add_field => ["source", "%s"]
                add_field => ["source_host", "%s"]
        }
        file {
                type => "nginx_error"
                path => ["/var/log/nginx/%s_error.log"]
                exclude => ["*.gz"]
                sincedb_path => "/opt/logstash"
                debug => true
                add_field => ["source", "%s"]
                add_field => ["source_host", "%s"]
        }
}"""

@task
def deploy(projectName, ci):
    if projectName not in env.projects:
        print('%s not found in list of known projects')
    else:
        if not exists('/etc/andyet_ops_bootstrap'):
            print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
        else:
            if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
                project       = env.projects[projectName]
                projectConfig = getProjectConfig(projectName, ci, env.host_string)

                project['logs'] = { "bucker": [],
                                    "nginx": [],
                                  }

                if 'tasks' in project:
                    for task in project['tasks']:
                        execute('fabops.andyet.deploy_task', projectName, task, ci)

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

                if 'tasks' in project and 'logstash' in project['tasks']:
                    s = ''
                    if len(project['logs']['bucker']) > 0:
                        for item in project['logs']['bucker']:
                            s += _logstash_bucker % (item, item)
                        for item in project['logs']['nginx']:
                            s += _logstash_nginx % (item, item, env.host_string, item, item, env.host_string)

                    projectConfig['logstash_files'] = s

                    upload_template('templates/logstash/logstash.conf',
                                    '/etc/logstash/logstash.conf',
                                    context=projectConfig, use_sudo=True)

def deployScripts(projectName, projectConfig):
    static = 'repository_site.url' in projectConfig
    if static:
        s = 'static'
    else:
        s = 'node'
    deployFile = 'deploy_%s' % s

    print 'STATIC', static

    with settings(user=projectConfig['deploy_user']):
        deploySeen = False
        if 'scripts' in projectConfig:
            for f in projectConfig['scripts']:
                if f == 'deploy.sh':
                    deploySeen = True
                upload_template(os.path.join(projectConfig['configDir'], f), f, context=projectConfig)
                run('chmod +x %s' % os.path.join(projectConfig['homeDir'], f))

        if not deploySeen:
            upload_template('templates/%s.sh' % deployFile, 'deploy.sh', context=projectConfig)
            run('chmod +x %s' % os.path.join(projectConfig['homeDir'], 'deploy.sh'))

    if static:
        deployStatic(projectName, projectConfig)

def deployStatic(projectName, projectConfig):
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
        projectConfig['siteKey'] = siteKey
    else:
        siteKey = projectConfig['deploy_key']
        projectConfig['siteKey'] = ''

    if 'repository_site.branch' in projectConfig:
        deployBranch = projectConfig['repository_site.branch']
    else:
        deployBranch = projectConfig['deploy_branch']

    with settings(user=projectConfig['deploy_user']):
        if exists(tempDir):
            run('rm -rf %s' % tempDir)

        run('mkdir -p %s' % targetDir)
        run('mkdir -p %s' % workDir)

        run('ssh-add -D; ssh-add .ssh/%s' % siteKey)
        run('git clone %s %s' % (repoUrl, workDir))

        with cd(workDir):
            if run('git checkout %s' % deployBranch):
                run('cp -r %s/* %s' % (workDir, targetDir))

def updateProject(projectName, projectConfig):
    if 'nginx.sitename' in projectConfig and os.path.exists(os.path.join(projectConfig['configDir'], '%s.nginx' % projectConfig['name'])):
        execute('fabops.nginx.deploy', projectConfig)

    if 'prosody.vhost' in projectConfig:
        execute('fabops.prosody.deploy', projectConfig)

    if 'runit.start' in projectConfig:
        execute('fabops.runit.update_app', projectConfig)
        if projectConfig['runit.type'] == 'node':
            projectConfig['restart'] = 'sv restart %s' % projectConfig['name']
            execute('fabops.nodejs.deploy', projectConfig)

    deployScripts(projectName, projectConfig)

    if 'node_app' in projectConfig:
        with settings(user=projectConfig['deploy_user']):
            execute('fabops.nodejs.deploy', projectConfig)

    if 'node_apps' in projectConfig:
        with settings(user=projectConfig['deploy_user']):
            for app in projectConfig['node_apps']:
                run('npm i -g %s' % app)

@task
def deploy_task(projectName, taskName, ci):
    if not exists('/etc/andyet_ops_bootstrap'):
        print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
    else:
        if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
            if projectName in env.projects and env.host_string in env.projects[projectName]['hosts']:
                projectConfig = getProjectConfig(projectName, ci, env.host_string)
                if taskName in ('nginx', 'redisWeb', 'redisApi', 'errorTests', 'logstash', 'riak'):
                    execute('fabops.andyet.%s' % taskName, taskName, projectConfig)

@task
def update_app(projectName, appName, ci):
    if not exists('/etc/andyet_ops_bootstrap'):
        print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
    else:
        if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
            if projectName in env.projects and env.host_string in env.projects[projectName]['hosts']:
                projectConfig = getProjectConfig(projectName, ci, env.host_string)
                project       = env.projects[projectName]

                if 'apps' in project and appName in project['apps']:
                    execute('fabops.nodejs.deploy', projectName, projectConfig, force=False)

@task
def opsbot_status(projectName, ci):
    if not exists('/etc/andyet_ops_bootstrap'):
        print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
    else:
        if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
            checkHost(projectName, ci)

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
def opsbot_deploy(projectName, ci):
    if not exists('/etc/andyet_ops_bootstrap'):
        print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
    else:
        if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
            checkHost(projectName, ci)

            if projectName in env.projects and env.host_string in env.projects[projectName]['hosts']:
                projectConfig = getProjectConfig(projectName, env.host_string)
                project       = env.projects[projectName]

                updateProject(projectName, projectConfig)

@task
def opsbot_service(projectName, ci, state):
    if not exists('/etc/andyet_ops_bootstrap'):
        print("fabops.provision.bootstrap has NOT been run, cancelling deploy")
    else:
        if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
            checkHost(projectName, ci)

            if projectName in env.projects and env.host_string in env.projects[projectName]['hosts']:
                projectConfig = getProjectConfig(projectName, env.host_string)
                project       = env.projects[projectName]

                if 'upstart.type' in projectConfig:
                    sudo('service %s %s' % (projectName, state))
                else:
                    sudo('sv %s %s' % (state, projectName))

@task
def opsbot_start(projectName, ci):
    execute('fabops.andyet.opsbot_service', projectName, ci, 'start')

@task
def opsbot_stop(projectName, ci):
    execute('fabops.andyet.opsbot_service', projectName, ci, 'stop')

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
    fabops.riak.deploy(taskName)

@task
def logstash(taskName, projectConfig):
    execute('fabops.logstash.install', projectConfig)
