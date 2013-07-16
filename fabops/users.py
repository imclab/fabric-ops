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

_sshagent_autostart = """SSHENV=~/.ssh/agent-${HOSTNAME}
if [ ! -f "${SSHENV}" ]; then
    ssh-agent > ${SSHENV}
fi
. ${SSHENV}"""


@task
def adduser(username, keyfile=None, sudoer=False):
    """
    Create a new user with the specified username. 
    If keyfile is specified, the public key will also be uploaded.
    If sudoer=True, the user will be added to the sudo group
    """
    if not fabops.common.user_exists(username):
        sudo('useradd -m -c %s -s /bin/bash %s' % (username, username))
        append('/home/%s/.profile' % username, _sshagent_autostart, use_sudo=True)

        sshDir   = fabops.common.ssh_make_directory(username)
        pkeyFile = '%spkey.sh' % sshDir
        if not exists(pkeyFile):
            put('templates/pkey.sh', pkeyFile, use_sudo=True)
            sudo('chown %s:%s %s' % (username, username, pkeyFile))
            sudo('chmod 700 %s' % pkeyFile)
    else:
        print('User %s already exists' % username)

    if sudoer:
        sudo('gpasswd -a %s sudo' % username)
    if keyfile is not None:
        authorizekey(username, keyfile)

@task
def disableuser(username):
    """
    Disable logins for the user by removing their authorized_keys file
    """
    if fabops.common.user_exists(username):
        userhome = fabops.common.get_home(username)
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
    if fabops.common.user_exists(username):
        userhome = fabops.common.get_home(username)
        if exists('%s/.ssh/authorized_keys.disabled' % userhome, use_sudo=True):
            sudo('mv %s/.ssh/authorized_keys.disabled %s/.ssh/authorized_keys' % (userhome, userhome))
        else:
            print('User %s was not disabled' % username)
    else:
        print('User %s does not exist' % username)

def addkeyfile(username, keyfile, keyfilename):
    remote = fabops.common.ssh_make_directory(username)
    upload_template(keyfile, '%s/%s' % (remote, keyfilename), use_sudo=True)
    sudo('chown %s:%s %s/%s' % (username, username, remote, keyfilename))
    sudo('chmod 600 %s/%s' % (remote, keyfilename))

@task
def addprivatekey(username, keyfile):
    """
    Adds keyfile to username's home directory as a private key
    """
    addkeyfile(username, keyfile, 'id_rsa')

    with settings(warn_only=True):
        sudo("ssh -o StrictHostKeyChecking=no git@github.com", user=username)

@task
def adddeploykey(username, keyfile, keyfilename):
    """
    Adds a deploy keyfile to username's home directory as an additional private key
    """
    addkeyfile(username, keyfile, keyfilename)

    with settings(warn_only=True, user=username, use_sudo=True):
        run('ssh-add .ssh/%s' % keyfilename)
        run("ssh -o StrictHostKeyChecking=no git@github.com")

@task
def authorizekey(username, keyfile):
    """
    Add the key to the user's authorized_keys file                                                                                                                                           
    """
    remote = fabops.common.ssh_make_directory(username)
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
    remote = fabops.common.ssh_make_directory(username)
    f = open(keyfile)
    key = f.read().strip()
    f.close()
    remoteFile = remote + os.sep + 'authorized_keys'
    sudo("cp %s %s.tmp" % (remoteFile, remoteFile))
    sudo("fgrep -v '%s' %s.tmp > %s" % (key, remoteFile, remoteFile))
