#!/usr/bin/env python

# :copyright: (c) 2013 by &yet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

import os

from fabric.operations import *
from fabric.api import *
from fabric.contrib.files import *
from fabric.colors import *
from fabric.context_managers import cd

import fabops.common
import fabops.users
import fabops.nginx

_node_version = 'v0.8.18'
_nvm_url      = 'https://github.com/creationix/nvm.git'

@task
def install_Node(user, nodeVersion, installDir):
    """
    Install nvm into a user's directory
    NOTE: the working assumption is that nvm is being installed into
          a working user's home dir - it will modify the ~/.profile
          of the user and that the home dir is /home/username
    """
    with settings(user=user):
        nvmDir = os.path.join(installDir, '.nvm')

        if exists(nvmDir):
            print('nvm already installed at %s' % nvmDir)
        else:
            with cd(installDir):
                run('git clone %s .nvm' % _nvm_url)
                append(os.path.join(installDir, '.profile'), '. ~/.nvm/nvm.sh\n')

        with cd(installDir):
            run('. %s/.nvm/nvm.sh; nvm install %s' % (installDir, nodeVersion))
            run('. %s/.nvm/nvm.sh; nvm use %s; nvm alias default %s' % (installDir, nodeVersion, nodeVersion))

@task
def install_app(appConfig):
    """
    Install a node app
    """
    packageJson = appConfig['app_details']['package']

    if 'engines' in packageJson:
        nodeVersion = packageJson['engines']['node']
        nodeVersion = 'v%s' % nodeVersion.split('=', 1)[1]
    else:
        nodeVersion = _node_version

    if fabops.common.user_exists(appConfig['deploy_user']):
        with settings(user=appConfig['deploy_user']):
            install_Node(appConfig['deploy_user'], nodeVersion,  appConfig['home_dir'])

            if not exists(appConfig['app_dir']):
                with cd(appConfig['home_dir']):
                    run('git clone %s %s' % (appConfig['repository']['url'], appConfig['app_dir']))

            deploy_app(appConfig)

@task
def deploy_app(appConfig):
    """
    Deploy (aka update) an installed node app
    """
    if fabops.common.user_exists(appConfig['deploy_user']):
        with settings(user=appConfig['deploy_user']):
            if exists(appConfig['app_dir']):
                with cd(appConfig['app_dir']):
                    run('git pull origin %s' % appConfig['deploy_branch'])

                with cd(appConfig['app_dir']):
                    run('. %s/.nvm/nvm.sh; npm install' % appConfig['home_dir'])
