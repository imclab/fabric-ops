#!/bin/bash

./deploy.sh

echo "updating bookbuilder repo"

cd /home/%(deploy_user)s/bookbuilder
git pull origin master
git fetch
npm i --production

ssh-add -D
ssh-add ~/.ssh/%(deploy_key)s

echo "running grunt task to build book"
grunt
