#!/usr/bin/env python

# :copyright: (c) 2013 by AndYet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

from fabric.operations import *
from fabric.api import *
from fabric.contrib.files import *
from fabric.colors import *
from fabric.context_managers import cd

import json
import common
import users
import nginx


_node_version = 'v0.8.18'
_nvm_url      = 'https://github.com/creationix/nvm.git'


@task
def nodeapp(appname, appconfig):
    """
    Install a node app
    """
    if 'user' in appconfig:
        appuser = appconfig['user']
    else:
        appuser = appname
    
    appurl      = appconfig['git_repo']
    packageUrl  = appconfig['package']
    packageFile = '%s/package.json' % os.env['TMPDIR']
    
    local('curl %s > %s' % (packageUrl, packageFile))

    package = json.load(open(packageFile, 'r'))

    if 'engines' in package:
        nodeVersion = package['engines']['node']
        nodeVersion = 'v%s' % nodeVersion.split('=', 1)[1]
    else:
        nodeVersion = _node_version

    if not common.user_exists(appuser):
        users.adduser(appuser)

    if common.user_exists(appuser):
        homedir = '/home/%s' % appuser

        if not exists('%s/.nvm' % homedir):
            with cd(homedir):
                sudo('git clone %s .nvm' % _nvm_url, user=appuser)
                append(os.path.join(homedir, '.profile'), '. ~/.nvm/nvm.sh\n', use_sudo=True)

                sudo('. %s/.nvm/nvm.sh; nvm install %s; nvm use %s' % (homedir, _node_version, _node_version), user=appuser)

        if exists('%s/signalmaster' % homedir):
            with cd('%s/signalmaster' % homedir):
                sudo('git pull')
        else:
            with cd(homedir):
                sudo('git clone %s' % appurl)

        sudo('. %s/.nvm/nvm.sh; npm install')

    if 'nginx' in appconfig:
        for site in appconfig['nginx']:
            nginx.site(site)

@task
def install():
    for app in env.apps.keys():
        appconfig = env.apps[app]

        if appconfig['language'] == 'node':
            nodeapp(app, appconfig)
