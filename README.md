# pyddhcpd - Server for distributed DHCP

[![Build Status](https://api.travis-ci.org/tcatm/pyddhcpd.svg?branch=master)](https://travis-ci.org/tcatm/pyddhcpd)


# Dependencies

- Python 3.4

# Installation

Most Gateways still run on Debian wheezy which does not contain Python 3.4 in its repositories, so you can install a virtualenv like this:

```
echo "build and install 3.4.3 as root"
P3PATH=/home/$USER/Python3
mkdir -p $P3PATH
cd $P3PATH
wget https://www.python.org/ftp/python/3.4.3/Python-3.4.3.tgz
tar -zxvf Python-3.4.3.tgz
cd Python-3.4.3
./configure --prefix=$P3PATH/Python-3.4.3
make; make install


cd /opt/
git clone https://github.com/tcatm/pyddhcpd.git
```
you have to adapt your config.py to your needs 

```
echo "start Python 3.4.3 environment"
$P3PATH/Python-3.4.3/bin/pyvenv py3env
source py3env/bin/activate
echo "start pyddhcpd"
python3 /opt/pyddhcpd/pyddhcpd.py
```

# Links

* Concept: https://gist.github.com/tcatm/2dd0e6699f2a153505d0#file-ddhcpd-md
* Sandbox: Firmware: http://map.sb.freifunk.ruhr/gluon/experimental/20
* Forum: https://forum.freifunk.net/t/experimenteller-server-fuer-verteiltes-dhcp
