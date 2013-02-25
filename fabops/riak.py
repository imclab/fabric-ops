#!/usr/bin/env python

# :copyright: (c) 2013 by AndYet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

from fabric.operations import *
from fabric.api import *
from fabric.contrib.files import *
from fabric.colors import *
from fabric.context_managers import cd

import fabops.common


@task
def install():
    """
    Install riak
    Prepare Ubuntu to install Riak from the basho repository

    Force install by calling as riak.install:true
    """
    sudo('curl http://apt.basho.com/gpg/basho.apt.key | sudo apt-key add -')

    if not exists('/etc/apt/sources.list.d/basho.list'):
        sudo('echo deb http://apt.basho.com $(lsb_release -sc) main > /etc/apt/sources.list.d/basho.list')

    sudo('apt-get update')
    sudo('apt-get install riak')
