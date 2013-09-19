#!/bin/bash

./deploy.sh

WORKDIR="/home/%(deploy_user)s/work"
POSTS="${WORKDIR}/posts"

ssh-add -D
ssh-add .ssh/%(repository_site.key)s

rm -rf ${POSTS}
mkdir -p ${WORKDIR}
cd ${WORKDIR}

git clone %(repository_site.url)s ${POSTS}

cp ${POSTS}/* /home/andyet-blog/articles/