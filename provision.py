#!/usr/bin/env python

# :copyright: (c) 2013 by AndYet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

from fabric.operations import *
from fabric.api import *
from fabric.contrib.files import *
from fabric.colors import *
from fabric.context_managers import cd

import common
import users

@task
def upgrade():
    """
    Update the apt cache and perform an upgrade
    """
    if sudo('DEBIAN_FRONTEND=noninteractive apt-get update').failed:
        abort()
    if sudo('DEBIAN_FRONTEND=noninteractive apt-get upgrade -y').failed:
        abort()
    if sudo('DEBIAN_FRONTEND=noninteractive apt-get autoremove -y').failed:
        abort()

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
def install_package(package):
    """
    Install and configure
    """
    sudo('DEBIAN_FRONTEND=noninteractive apt-get install -y %s' % package)

@task
def create_instance():
    """
    Create and setup an empty server
    """
    pass

@task
def bootstrap():
    """
    Bootstrap a single given server
    The server is checked for upgrades and the ops user is
    installed so that fabric can be used going forward
    """
    print('-'*42)
    print('Bootstrapping OS for a single host.  Fabric user is being forced to "root".')
    print('-'*42)

    env.user = 'root'

    upgrade()
    disablex11()
    for p in ('ntp', 'fail2ban', 'screen'):
        install_package(p)
    users.adduser('ops', 'ops.keys', True)
    append('/etc/sudoers', '%ops    ALL=(ALL:ALL) NOPASSWD: ALL\n')

    # TODO enable these after we are *sure* things are working with SSH for ops user
    # disableroot()
    # disablepasswordauth()

@task(default=True)
def configure():
    """
    Configure the server with the baseline packages
    """
    for p in ('build-essential', 'git'):
        install_package(p)
