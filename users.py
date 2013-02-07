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


@task
def adduser(username, keyfile=None, sudoer=False):
    """
    Create a new user with the specified username. If keyfile is specified, the public key will also be uploaded. If sudoer=True, the user will be added to the sudo group
    """
    if not common.user_exists(username):        
        sudo('useradd -m -c %s -s /bin/bash %s' % (username, username))
        if sudoer:
            sudo('gpasswd -a %s sudo' % username)
        if keyfile is not None:
            authorizekey(username, keyfile)
    else:
        print('User %s already exists' % username)

@task
def disableuser(username):
    """
    Disable logins for the user by removing their authorized_keys file
    """
    if common.user_exists(username):
        userhome = common.get_home(username)
        if not exists('%s/.ssh/authorized_keys.disabled' % userhome):
            sudo('mv %s/.ssh/authorized_keys %s/.ssh/authorized_keys.disabled' % (userhome, userhome))
        else:
            print('User %s is already disabled' % username)
    else:
        print('User %s does not exist' % username)

@task
def enableuser(username):
    """
    Enable a disabled user by moving their authorized_keys file back into place
    """
    if common.user_exists(username):
        userhome = common.get_home(username)
        if exists('%s/.ssh/authorized_keys.disabled' % userhome, use_sudo=True):
            sudo('mv %s/.ssh/authorized_keys.disabled %s/.ssh/authorized_keys' % (userhome, userhome))
        else:
            print('User %s was not disabled' % username)
    else:
        print('User %s does not exist' % username)

@task
def addprivatekey(username, keyfile):
    """
    Adds keyfile to username's home directory as a private key
    """
    remote = common.ssh_make_directory(username)
    upload_template(keyfile, '%s/id_rsa' % remote, use_sudo=True)
    sudo('chown %s:%s %s/id_rsa' % (username, username, remote))
    sudo('chmod 600 %s/id_rsa' % remote)
    with settings(warn_only=True):
        sudo("ssh -o StrictHostKeyChecking=no git@github.com", user=username)

@task
def authorizekey(username, keyfile):
    """
    Add the key to the user's authorized_keys file                                                                                                                                           
    """
    remote = ssh_make_directory(username)
    f = open(keyfile)
    append(remote + os.sep + 'authorized_keys', f.read(), use_sudo=True)
    f.close()
    sudo('chown %s:%s %s/*' % (username, username, remote))
    sudo('chmod 600 %s/*' % remote)

@task
def revokekey(username, keyfile):
    """
    Remove the key from the user's authorized_keys file
    """
    remote = common.ssh_make_directory(username)
    f = open(keyfile)
    partial_key = f.read().strip()
    partial_key = re.escape(partial_key.split()[-1])
    f.close()
    sudo('sed -i /^ssh-.*%s/d %s' % (partial_key, remote + os.sep + 'authorized_keys'))
