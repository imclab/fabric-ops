#!/usr/bin/env python

import os
import os.path
import sys
import json
import types
import logging

from optparse import OptionParser

_ourPath = os.getcwd()
_ourName = os.path.splitext(os.path.basename(sys.argv[0]))[0]

def loadJson(jsonFile):
    result   = None
    filename = os.path.expanduser(jsonFile)
    if os.path.isfile(filename):
        result = json.loads(' '.join(open(filename, 'r').readlines()))
    return result

class BearConfig(object):
    def __init__(self, configFilename=None):
        """ Parse command line parameters and populate the options object
        """
        self.options        = None
        self.appPath        = _ourPath
        self.configFilename = configFilename
        self.config         = {}

        # these are my normal defaults
        self.bears_config   = { 'configFile':  ('-c', '--config',  self.configFilename, 'Configuration Filename (optionally w/path'),
                              }

    def findConfigFile(self, paths=None, envVar=None):
        searchPaths = []

        if paths is not None:
            for path in paths:
                searchPaths.append(path)

        for path in (_ourPath, os.path.expanduser('~')):
            searchPaths.append(path)
        
        if envVar is not None and envVar in os.environ:
            path = os.environ[envVar]
            searchPaths.append(path)

        for path in searchPaths:
            s = os.path.join(path, self.configFilename)
            if os.path.isfile(s):
                self.options.configFile = s

    def addConfig(self, key, shortCmd='', longCmd='', defaultValue=None, helpText=''):
        if len(shortCmd) + len(longCmd) == 0:
            logging.error('You must provide either a shortCmd or a longCmd value - both cannot be empty')
        elif key is None and type(key) is types.StringType:
            logging.error('The configuration key must be a string')
        else:
            self.config[key] = (shortCmd, longCmd, defaultValue, helpText)

    def load(self, defaults=None, configPaths=None, configEnvVar=None):
        parser        = OptionParser()
        self.defaults = {}

        if defaults is not None:
            for key in defaults:
                self.defaults[key] = defaults[key]

        # load my config items, but just in case the caller has other ideas
        # do not load them if the key is already present
        # TODO need to add some way to also cross check short/long command values
        for key in self.bears_config:
            if key not in self.config:
                self.config[key] = self.bears_config[key]

        for key in self.config:
            items = self.config[key]

            (shortCmd, longCmd, defaultValue, helpText) = items

            if type(defaultValue) is types.BooleanType:
                parser.add_option(shortCmd, longCmd, dest=key, action='store_true', default=defaultValue, help=helpText)
            else:
                parser.add_option(shortCmd, longCmd, dest=key, default=defaultValue, help=helpText)

        (self.options, self.args) = parser.parse_args()

        if self.options.configFile is not None:
            self.findConfigFile(configPaths, configEnvVar)
            self.options.config = self.loadJSON(self.options.configFile)

    def loadJSON(self, filename):
        """ Read, parse and return given config file
        """
        jsonConfig = {}

        if os.path.isfile(filename):
            try:
                logging.debug('attempting to load json config file [%s]' % filename)
                jsonConfig = json.loads(' '.join(open(filename, 'r').readlines()))
            except:
                logging.error('error during loading of config file [%s]' % filename, exc_info=True)

        return jsonConfig
