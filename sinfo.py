#!/usr/bin/env python

import os
import time
import json

import pyrax
from bearlib import BearConfig


_data_centers = [ 'DFW', 'ORD' ]
_commands     = [ 'list' ]
_config_file  = '~/.rackspace.cfg'

_usage = """
    Usage: python sinfo.py [options] COMMAND

    Where [options] can be one of:
        -d | --datacenter  datacenter to work within, choices are
                           %s
                           default is all of them
        -c | --config      where to retrieve configuration items and the
                           rackspace API keys.
                           default is %s

    and where COMMAND is one of:
        list SERVER
                        list details for the servers.
                          Optionally give a SERVER name to focus on.
                          If a datacenter has been given, the list will only
                          contain those servers.

    Config File:
        [rackspace_cloud]
        username = USERNAME
        api_key = KEY
""" % (_data_centers, _config_file)

def loadConfig():
    cfg = BearConfig(_config_file)

    cfg.addConfig('datacenter', '-d', '--datacenter', 'ALL')

    cfg.load()

    return cfg.options, cfg.args

def initCredentials(datacenter):
    pyrax.set_setting("identity_type", "rackspace")
    pyrax.set_credential_file(os.path.expanduser(cfg.configFile), datacenter)

def loadServers(datacenters):
    #flv = cs.flavors.find(name='1GB Standard Instance')
    #img = cs.images.find(name='secteam-scan-server')
    #srv = cs.servers.create('secteam-test', img, flv)
    #pyrax.utils.wait_for_build(srv, verbose=True)
    #print "Your server is now ready. Public IP is", srv['public'][0], srv['public'][1]

    # {'OS-EXT-STS:task_state': None, 
    #  'addresses': { u'public': [], 
    #                 u'private': []
    #               }, 
    #  'links': [],
    #  'image': { u'id': u'b83c860d-16e2-41c9-9f3a-3d5a00743afc', 
    #             u'links': []
    #           }, 
    #  'manager': <novaclient.v1_1.servers.ServerManager object at 0x101abb450>, 
    #  'OS-EXT-STS:vm_state': u'active', 
    #  'flavor': { u'id': u'2', 
    #              u'links': []
    #            }, 
    #  'id': u'', 
    #  'user_id': u'NNN', 
    #  'OS-DCF:diskConfig': u'AUTO', 
    #  'accessIPv4': u'', 
    #  'accessIPv6': u'', 
    #  'progress': 100, 
    #  'OS-EXT-STS:power_state': 1, 
    #  'metadata': {}, 
    #  'status': u'ACTIVE', 
    #  'updated': u'2013-04-25T05:11:09Z', 
    #  'hostId': u'', 
    #  'key_name': None, 
    #  'name': u'sssss', 
    #  'created': u'2013-02-11T19:33:31Z', 
    #  'tenant_id': u'NNN', 
    #  '_info': {}, 
    #  'config_drive': u'', 
    #  '_loaded': True
    # }
    result = {}
    for dc in datacenters:
        initCredentials(dc)

        cs = pyrax.cloudservers
        for s in cs.servers.list(detailed=True):
            if s.name not in result:
                result[s.name] = None
            result[s.name] = s
    return result

def getServerInfo(serverName, serverList):
    result = None

    if cfg.datacenter == 'ALL':
        s = ' in server list'
    else:
        s = ' in datacenter %s' % cfg.datacenter

    print serverName, serverName in serverList

    if serverName not in serverList:
        print '%s not found %s' % (serverName, s)
    else:
        item   = serverList[serverName]
        result = {}
        for key in ( 'accessIPv4', 'status', 'name' ):
            result[key] = item.__getattr__(key)

    return result

def getCommandParam(cmdText, commands):
    # index() will return an exception if the item
    # is not in the list, so we can return an empty
    # string if that happens
    try:
        p      = commands.index(cmdText)
        result = commands[p+1]
    except:
        result = ''
    return result

if __name__ == '__main__':
    cfg, commands = loadConfig()

    if len(commands) == 0:
        print _usage
    else:
        if cfg.datacenter == 'ALL':
            datacenters = _data_centers
        else:
            datacenters = [ datacenter ]

        servers = loadServers(datacenters)
        results = []

        if 'list' in commands:
            serverName = getCommandParam('list', commands)

            if serverName in _commands or len(serverName) == 0:
                serverName = None

            if serverName is not None:
                r = getServerInfo(serverName, servers)
                if r is not None:
                    results.append(r)
            else:
                for s in servers:
                    r = getServerInfo(s, servers)
                    if r is not None:
                        results.append(r)

        print json.dumps(results)