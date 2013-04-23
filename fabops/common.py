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

_ourPath = os.getcwd()

def list_files(path):
    return [ f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) ]

def list_dirs(path):
    return [ d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)) ]

def is_installed(package):
    with settings(hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
        out = run('dpkg -s %s' % package)
        for line in out.splitlines():
            if line.startswith("Status: "):
                s = line[8:]
                if "installed" in s.split():
                    return True
        return False

def flatten(source, namespace=None):
    result = {}
    for key in source:
        if namespace is None:
          s = key
        else:
          s = '%s.%s' % (namespace, key)
        if isinstance(source[key], dict):
            d = flatten(source[key], s)
            for k in d:
              result[k] = d[k]
        else:
            result[s] = source[key]
    return result

def preseed_package(package, values):
    for q_name, _ in values.items():
        q_type, q_answer = _
        sudo('echo "%(package)s %(q_name)s %(q_type)s %(q_answer)s" | debconf-set-selections' % locals())

@task
def find_package(package):
    with settings(warn_only = True):
        run('dpkg --list | grep "ii  " | grep %s' % package)

@task
def install_package(package):
    """
    Install and configure
    """
    sudo('DEBIAN_FRONTEND=noninteractive apt-get install -y %s' % package)

def user_exists(username):
    """
    See if a user exists
    """
    with settings(warn_only = True):
        return 'No such user' not in run('id %s' % username)

def get_home(username):
    """
    Return a path to the home directory of the user
    """
    if username == 'root':
        remote = '/root'
    else:
        remote = '/home/%s' % username
    return remote

def ssh_make_directory(username):
    """
    If it doesn't exist, create the .ssh directory in a user's home. Returns the path to the user's .ssh (ie: /home/username/.ssh)
    """
    remote = '%s/.ssh/' % get_home(username)
    if not exists('%s' % remote, use_sudo=True):
        sudo('mkdir %s' % remote)
        sudo('chown %s:%s %s' % (username, username, remote))
        sudo('chmod 700 %s' % remote)
    return remote

def config(cfgFilename='fabric.cfg'):
    """
    Load a json configuration file that contains values used by
    the fabric environment
    """
    filename = os.path.join(_ourPath, cfgFilename)
    cfg      = json.load(open(filename, 'r'))

    setattr(env, 'our_path', _ourPath)
    setattr(env, 'sites',    {})

    for opt in cfg.keys():
        if opt in ('user', 'key_filename', 'hosts', 'nginx', 'haproxy', 'redis', 'riak', 'app_dir', 'site_dir', 'pinned'):

            if opt == 'hosts':
                # "hosts": [ { "host": "data2",
                #              "role": ["app"]
                #            }
                #          ]
                for h in cfg[opt]:
                    hostname = h['host']
                    roles    = h['role']
                    for r in roles:
                        if r not in env.roledefs:
                            env.roledefs[r] = []
                        env.roledefs[r].append(hostname)
                    if 'site' in h:
                        sites = h['site']
                        for site in sites:
                            if hostname not in env.sites:
                                env.sites[hostname] = []
                            env.sites[hostname].append(site)
            else:
                setattr(env, opt, cfg[opt])
