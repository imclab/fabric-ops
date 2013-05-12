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
import fabops.redis

def areWeQA(roles):
    """Look at list of roles and see if QA is included.

    If so, remove it from roles and set the returned flag to True
    """
    flag   = False
    target = None
    for s in roles:
        if s.lower() == 'qa':
            flag   = True
            target = s
            break
    if flag:
        roles = [ r for r in roles if r != target ]
    return flag, roles

@task
def deploy():
    if not exists('/etc/andyet_ops_bootstrap'):
        execute('fabops.provision.bootstrap')

    if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
        roles = []
        isQA  = False

        if len(env.roles) == 0:
            for r in env.roledefs:
                if env.host_string in env.roledefs[r]:
                    roles.append(r)

            isQA, roles = areWeQA(roles)
            print isQA, roles
            for r in roles:
                execute('fabops.andyet.%s' % r, r, qa=isQA, hosts=[ env.host_string, ])

            if env.host_string in env.sites:
                for site in env.sites[env.host_string]:
                    execute('fabops.provision.site_install', site, qa=isQA)

            if env.host_string in env.apps:
                for app in env.apps[env.host_string]:
                    execute('fabops.provision.app_install', app, qa=isQA)
        else:
            isQA, roles = areWeQA(env.roles)
            for r in roles:
                execute('fabops.andyet.%s' % r, r, qa=isQA)

@task
def deploy_apps(appname=None):
    if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
        if env.host_string in env.apps:
            if appname is not None:
                if appname in env.apps[env.host_string]:
                    fabops.provision.app_deploy(appname)
            else:
                for app in env.apps[env.host_string]:
                    fabops.provision.app_deploy(app)
    else:
        print("deploy_apps called for a host that is not bootstrapped")

@task
def deploy_sites(sitename=None):
    if fabops.common.user_exists('ops') and exists('/etc/andyet_ops_bootstrap', use_sudo=True):
        roles = []
        isQA  = False

        if env.host_string in env.sites:
            if sitename is not None:
                if sitename in env.sites[env.host_string]:
                    fabops.provision.site_deploy(sitename)
            else:
                for site in env.sites[env.host_string]:
                    fabops.provision.site_deploy(site)

@task
def redis_web(rolename, qa=False):
    print('redis_web: role=%s qa=%s' % (rolename, qa))
    fabops.redis.deploy(rolename, qa)

@task
def redis_api(rolename, qa=False):
    print('redis_api: role=%s qa=%s' % (rolename, qa))
    fabops.redis.deploy(rolename, qa)

@task
def riak(rolename, qa=False):
    print('riak: qa=%s' % qa)
    fabops.riak.deploy(qa)

@task
def prod(rolename, qa=False):
    print "prod", rolename, qa

@task
def andbang_web(rolename, qa=False):
    print "andbang_web", rolename, qa

@task
def haproxy(rolename, qa=False):
    fabops.haproxy.install()
