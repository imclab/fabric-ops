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
def deploy(projectConfig, force=True):
    """
    Deploy an installed node app

    assumes deploy user is already enabled
    """
    with settings(user=projectConfig['deploy_user'], use_sudo=True):
        repoKey = None
        if 'repo_keys' in projectConfig:
            repoKey = projectConfig['repo_keys'][0]
            projectConfig['repoKey'] = repoKey
        else:
            projectConfig['repoKey'] = ''
            # for repoKey in projectConfig['repo_keys']:
            #     run('ssh-add .ssh/%s' % repoKey)

        # if 'engines' in packageJson:
        #     nodeVersion = packageJson['engines']['node']
        #     if '=' in nodeVersion:
        #         nodeVersion = 'v%s' % nodeVersion.split('=', 1)[1]
        #     elif nodeVersion.startswith('~'):
        #         nodeVersion = nodeVersion[1:]
        # else:
        #     nodeVersion = _node_version
        if 'node' in projectConfig:
            nodeVersion = projectConfig['node']
        else:
            nodeVersion = _node_version

        if force and not exists(os.path.join(projectConfig['homeDir'], '.nvm')):
            install_Node(projectConfig['deploy_user'], nodeVersion,  projectConfig['homeDir'])

        if not exists(projectConfig['deploy_dir']):
            run('ssh-add -D; ssh-add ~/.ssh/%s' % projectConfig['deploy_key'])
            run('git clone %s %s' % (projectConfig['repository.url'], projectConfig['deploy_dir']))

        if exists(projectConfig['deploy_dir']):
            with cd(projectConfig['deploy_dir']):
                run('ssh-add -D; ssh-add ~/.ssh/%s' % projectConfig['deploy_key'])
                run('git pull origin %s' % projectConfig['deploy_branch'])
                run('git checkout %s' % projectConfig['deploy_branch'])

                if repoKey is not None:
                    run('ssh-add -D; ssh-add ~/.ssh/%s' % repoKey)
                run('. %s/.nvm/nvm.sh; npm install --production --color=false' % projectConfig['homeDir'])

        upload_template('templates/project_deploy.sh', 'deploy.sh', context=projectConfig)
        run('chmod +x %s' % os.path.join(projectConfig['homeDir'], 'deploy.sh'))

        if 'config_dir' in projectConfig:
            appConfigDir = projectConfig['config_dir']
        else:
            appConfigDir = projectConfig['appDir']

        appConfigDir = os.path.join(projectConfig['homeDir'], appConfigDir)

        upload_template(os.path.join(projectConfig['configDir'], 'production_config.json'),
                        os.path.join(appConfigDir,               'production_config.json'),
                        context=projectConfig)
