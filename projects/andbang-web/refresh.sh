#!/bin/bash

echo "refresh called with [${1}] and [${2}]"

if [ "$1" == "andbang.com" ]; then
  if [ "$2" == "refs/heads/beta" ]; then
    echo "processing andbang.com beta"

    ./deploy.sh
  fi
fi