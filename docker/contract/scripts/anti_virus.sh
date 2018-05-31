#
# MAKE NETWORK
#
sudo docker network create --subnet=192.168.56.0/24 user_defined_nw
sudo docker build -t trendmicro docker/trendmicro
sudo docker run -p 3000:3000 -i -v $(pwd):/tmp/share --net=user_defined_nw --ip=192.168.56.100 -t trendmicro /bin/bash
