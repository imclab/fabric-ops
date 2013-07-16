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

_sv_dir      = '/etc/sv'
_service_dir = '/etc/service'

def _init(projectConfig):
    projectConfig['serviceDir']  = os.path.join(_service_dir, projectConfig['name'])
    projectConfig['svDir']       = os.path.join(_sv_dir, projectConfig['name'])
    projectConfig['svRun']       = os.path.join(_sv_dir, projectConfig['name'], 'run')
    projectConfig['svEnv']       = os.path.join(_sv_dir, projectConfig['name'], 'env')
    projectConfig['svLog']       = os.path.join(_sv_dir, projectConfig['name'], 'log')
    projectConfig['svRunLog']    = os.path.join(_sv_dir, projectConfig['name'], 'log', 'run')
    projectConfig['svLogConfig'] = os.path.join(_sv_dir, projectConfig['name'], 'log', 'config')

@task
def init_app(projectConfig):
    """
    create the required service directories to enable
    runit to control/manage our apps
    """
    _init(projectConfig)
    if not exists(projectConfig['svDir']):
        sudo('mkdir %(svDir)s'           % projectConfig)
        sudo('chown root:root %(svDir)s' % projectConfig)

        sudo('mkdir %(svEnv)s'           % projectConfig)
        sudo('chown root:root %(svEnv)s' % projectConfig)

        sudo('mkdir %(svLog)s'           % projectConfig)
        sudo('chown root:root %(svLog)s' % projectConfig)

@task
def update_app(projectConfig, force=False, runTemplate='templates/node_runit', logrunTemplate='templates/runit_log', logconfigTemplate=None):
    _init(projectConfig)
    execute('fabops.runit.init_app', projectConfig)
    if force or not exists(projectConfig['svRun']):
        upload_template(runTemplate, projectConfig['svRun'], 
                        context=projectConfig,
                        use_sudo=True)
        sudo('chown root:root %(svRun)s' % projectConfig)
        sudo('chmod 755 %(svRun)s'       % projectConfig)
    if force or not exists(projectConfig['svRunLog']):
        upload_template(logrunTemplate, projectConfig['svRunLog'], 
                        context=projectConfig,
                        use_sudo=True)
        sudo('chown root:root %(svRunLog)s' % projectConfig)
        sudo('chmod 755 %(svRunLog)s'       % projectConfig)

        if logconfigTemplate is not None:
            upload_template(logconfigTemplate, projectConfig['svLogConfig'], 
                            context=projectConfig,
                            use_sudo=True)
            sudo('chown root:root %(svLogConfig)s' % projectConfig)
            sudo('chmod 755 %(svLogConfig)s'       % projectConfig)

    if 'runit.env' in projectConfig:
        for n,v in projectConfig['runit.env']:
            f = '%s/%s' % (projectConfig['svEnv'], n)
            if not exists(f):
                sudo('touch %s' % f)
            append(f, v % projectConfig, use_sudo=True)
            sudo('chown root:root %s' % f)

    sudo('mkdir -p %(logDir)s' % projectConfig)
    sudo('chown %(deploy_user)s:%(deploy_user)s %(logDir)s' % projectConfig)

@task
def disable_app(projectConfig):
    """
    disable the given app so runit will stop and not restart or manage
    the given app

    this is done by removing the /etc/service symlink that points to
    /etc/sv/<appname>
    """
    _init(projectConfig)
    sudo('rm -f %(serviceDir)s' % projectConfig)

@task
def enable_app(projectConfig):
    """
    enable the given app so runit will manage the given app

    this is done by adding the /etc/service symlink that points to
    /etc/sv/<appname>
    """
    _init(projectConfig)
    if exists(projectConfig['svDir']):
        sudo('ln -s %(svDir)s %(serviceDir)s' % projectConfig)
    else:
        print('unable to enable %(name)s - sv entry does not exist' % projectConfig)
