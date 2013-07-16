#!/usr/bin/env python

# :copyright: (c) 2013 by &yet
# :author:    Mike Taylor
# :license:   BSD 2-Clause

import os
import json
import shutil
import socket



def getSiteConfig(siteDir, siteName, qa=False):
    siteCfgDir  = os.path.join(os.path.abspath(siteDir), siteName)
    siteCfgFile = os.path.join(siteCfgDir, '%s.cfg' % siteName)
    siteConfig  = {}

    if os.path.exists(siteCfgFile):
        try:
            siteConfig = json.load(open(siteCfgFile, 'r'))
        except:
            print('error parsing configuration file %s' % siteCfgFile)
            print(sys.exc_info())
            siteConfig = {}

    siteConfig['qa']              = qa
    siteConfig['site_config_dir'] = siteCfgDir
    siteConfig['site_config']     = siteCfgFile

    if 'nginx' in siteConfig:
        s = ''
        if 'othernames' in siteConfig['nginx']:
            s = '%s ' % siteConfig['nginx']['othernames']
        s += siteConfig['nginx']['sitename']

        siteConfig['nginx']['servername'] = s

    return siteConfig

def getAppConfig(appDir, appName, qa=False):
    appCfgDir  = os.path.join(os.path.abspath(appDir), appName)
    appCfgFile = os.path.join(appCfgDir, '%s.cfg' % appName)
    appConfig  = {}

    if os.path.exists(appCfgFile):
        try:
            appConfig = json.load(open(appCfgFile, 'r'))
        except:
            print('error parsing configuration file %s' % appCfgFile)
            print(sys.exc_info())
            appConfig = {}

        appConfig['qa']             = qa
        appConfig['app_config_dir'] = appCfgDir
        appConfig['app_config']     = appCfgFile

        if 'deploy_user' not in appConfig:
            appConfig['deploy_user'] = appConfig['name']

        appConfig['home_dir'] = '/home/%s' % appConfig['deploy_user']
        appConfig['app_dir']  = os.path.join(appConfig['home_dir'], appConfig['name'])

        if 'deploy_config_dir' not in appConfig:
            appConfig['deploy_config_dir'] = ''

        appConfig['deploy_config_dir'] = os.path.join(appConfig['app_dir'], appConfig['deploy_config_dir'])

    return appConfig

def getAppDetails(appConfig):
    result = False

    if 'repository' in appConfig and appConfig['repository']['type'] == 'git':
        appName     = appConfig['name']
        gitRepoUrl  = appConfig['repository']['url']
        tempDir     = os.environ['TMPDIR']
        tempRepoDir = os.path.join(tempDir, appName)
    
        appConfig['app_details'] = { 'tempRepoDir': tempRepoDir,
                                     'language':    None,
                                   }

        # TODO need to make this work with the app's deploy key
        with cd(tempDir):
            if os.path.exists(tempRepoDir):
                shutil.rmtree(tempRepoDir)
            local('git clone %s %s' % (gitRepoUrl, tempRepoDir))

        if os.path.exists(tempRepoDir):
            packageFile = '%s/package.json' % tempRepoDir

            if os.path.exists(packageFile):
                appConfig['app_details']['language'] = 'node'
                try:
                    appConfig['app_details']['package'] = json.load(open(packageFile, 'r'))
                    result = True
                except:
                    print('error loading the package.json file %s' % packageFile)
                    print(sys.exc_info())
                    appConfig['app_details']['package'] = {}
            else:
                result = True
        else:
            print('unable to checkout repo for %s [%s]' % (appName, gitRepoUrl))

    return result
