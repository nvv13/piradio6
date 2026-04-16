#!/bin/bash


git add .
git commit -m "sync1"
git push


if [ -d /home/nvv/github.com/piradio6 ]; then
   rsync -r --links --exclude=.git --delete /home/nvv/gitflic.ru/piradio6 /home/nvv/github.com
   cd /home/nvv/github.com/piradio6
   git add .
   git commit -m "sync2"
   git push
fi
