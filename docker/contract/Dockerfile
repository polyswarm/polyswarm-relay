#
# Compile contracts to a mounted volume.
# Polyswarmd reads this this volume for subdirs.
# 
FROM ubuntu:17.10

ENV     ROOTDIR="/usr/src/app"
ENV     TRUFFLE="$ROOTDIR/truffle"
ENV     SHARE=""
VOLUME  $ROOTDIR

RUN     mkdir -p $ROOTDIR

WORKDIR $ROOTDIR

#
# Module Installation
#
RUN     apt-get -y update && apt-get install -y \
                                                \
          ruby                                  \
          git                                   \
          curl                                  \ 
          wget                                  \
          build-essential                       \
          gcc                                   \
          g++                                   \
          make                                  \ 
          sudo                                  \ 
          vim                                   \
          net-tools

RUN     curl -sL https://deb.nodesource.com/setup_10.x | bash -
RUN     apt-get -y install nodejs # Sine curl required, this is exceptional independent apt-get.
RUN     nodejs -v
RUN     npm -v
RUN     gem install colorize

#
# XXX   somehow clone does not work
#
# RUN     git clone https://github.com/polyswarm/polyswarm-contracts.git
# RUN     mv polyswarm-contracts truffle

COPY    $SHARE/polyswarm-contracts    ./truffle
COPY    $SHARE/scripts/mint_tokens.sh $TRUFFLE/mint_tokens.sh
COPY    $SHARE/scripts/post_bounty    $TRUFFLE/post_bounty

#
# Contract Compilation 
#
WORKDIR $TRUFFLE
COPY    $SHARE/scripts/truffle-config.js .
RUN     npm install -g truffle
COPY    $SHARE/node_modules node_modules
# RUN     git clone https://gitlab.com/keisugano/lfs-queenb.git --progress --verbose
# RUN     mv -v lfs-queenb/node_modules .
RUN     npm config rm proxy
RUN     npm config rm https-proxy
RUN     truffle compile

#
# Contract Migration part
#
COPY    $SHARE/scripts/migrate.sh /usr/local/bin/migrate
RUN     echo "netstat -ntlp | grep LISTEN" > /usr/local/bin/ports
RUN     chmod +x /usr/local/bin/migrate
RUN     chmod +x /usr/local/bin/ports

RUN     cp /usr/local/bin/migrate $ROOTDIR/migrate
