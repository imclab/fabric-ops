#!/usr/bin/env python

# :copyright: (c) 2013 by AndYet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

import os
import json
import shutil

from fabric.operations import *
from fabric.api import *
from fabric.contrib.files import *
from fabric.colors import *
from fabric.context_managers import cd

import common
import users
import nginx


_node_version = 'v0.8.18'
_nvm_url      = 'https://github.com/creationix/nvm.git'

@task
def installNode(user, nodeVersion, installDir=None):
    """
    Install nvm into a user's directory
    NOTE: the working assumption is that nvm is being installed into
          a working user's home dir - it will modify the ~/.profile
          of the user and that the home dir is /home/username
    """
    with settings(user=user):
        homeDir = os.path.join('/home', user)
        if installDir is None:
            installDir = homeDir
        nvmDir = os.path.join(installDir, '.nvm')

        if exists(nvmDir):
            print('nvm already installed at %s' % nvmDir)
        else:
            with cd(installDir):
                run('git clone %s .nvm' % _nvm_url)
                append(os.path.join(homeDir, '.profile'), '. ~/.nvm/nvm.sh\n')

        with cd(homeDir):
            run('. %s/.nvm/nvm.sh; nvm install %s' % (homeDir, nodeVersion))
            run('. %s/.nvm/nvm.sh; nvm use %s; nvm alias default %s' % (homeDir, nodeVersion, nodeVersion))

@task
def nodeapp(appConfig):
    """
    Install a node app
    """
    if 'deploy_user' in appConfig:
        deployUser = appConfig['deploy_user']
    else:
        deployUser = appConfig['name']

    deployKeyFile  = os.path.join(common._ourPath, 'keys', appConfig['deploy_key'])
    packageJson    = appConfig['app_details']['package']

    if 'engines' in packageJson:
        nodeVersion = packageJson['engines']['node']
        nodeVersion = 'v%s' % nodeVersion.split('=', 1)[1]
    else:
        nodeVersion = _node_version

    if not common.user_exists(deployUser):
        users.adduser(deployUser, 'ops.keys')

    if common.user_exists(deployUser):
        users.addprivatekey(deployUser, deployKeyFile)

        with settings(user=deployUser):
            homeDir = '/home/%s' % deployUser
            appDir  = os.path.join(homeDir, appConfig['name'])

            installNode(deployUser, nodeVersion)

            if exists(appDir):
                with cd(appDir):
                    run('git pull')
            else:
                with cd(homeDir):
                    run('git clone %s %s' % (appurl, appDir))

            with cd(appDir):
                run('. %s/.nvm/nvm.sh; npm install' % homeDir)

    d = { 'name':        appConfig['name'],
          'user':        deployUser,
          'appdir':      appDir,
          'description': appconfig['description'],
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

    sudo('chown %(appuser)s:%(appuser)s %(piddir)s' % d)
    sudo('chown %(appuser)s:%(appuser)s %(logdir)s' % d)

    if 'nginx' in appconfig:
        for site in appconfig['nginx']:
            nginx.site(site)

def getAppConfig(appName):
    appDir     = os.path.join(os.path.abspath(env.app_dir), appName)
    appCfgFile = os.path.join(appDir, '%s.cfg' % appName)

    if os.path.exists(appCfgFile):
        try:
            appConfig = json.load(open(appCfgFile, 'r'))
        except:
            appConfig = {}

    appConfig['app_dir']    = appDir
    appConfig['app_config'] = appCfgFile

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
                except:
                    appConfig['app_details']['package'] = {}
        else:
            print('unable to checkout repo for %s [%s]' % (appName, gitRepoUrl))
    else:
        print('currently only apps from git repos can be handled - skipping app install')

    return result

@task
def install(appName=None):
    if appName is None:
        print('no appName given, nothing to do')
    else:
        appConfig = getAppConfig(appName)

        if isinstance(appConfig, dict) and 'appname' in appConfig:
            if getAppDetails(appConfig):
                if appConfig['language'] == 'node':
                    nodeapp(appConfig)
        else:
            print('Unable to find (or load) the configuration file for %s in %s [%s]' % (appName, appDir, appCfgFile))

@task
def install_all():
    for d in common.list_dirs(env.app_dir):
        install(d)