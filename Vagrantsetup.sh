#!/usr/bin/env sh

eval "$(grep '^ID=' /etc/os-release)"

COMMON_PACKAGES="git pipx python3-pip vim kitty-terminfo zsh"
DEBIAN_PACKAGES="python3-venv"

if [ "$ID" = "fedora" ]; then
    sudo dnf update -y
    sudo dnf install -y $COMMON_PACKAGES
    cp /etc/skel/.zshrc /home/vagrant/.zshrc
    cp /etc/skel/.bashrc /home/vagrant/.bashrc
elif [ "$ID" = "debian" ]; then
    sudo apt update
    sudo apt dist-upgrade -y
    sudo apt install -y $COMMON_PACKAGES $DEBIAN_PACKAGES
    cp /etc/zsh/newuser.zshrc.recommended /home/vagrant/.zshrc
    cp /etc/skel/.bashrc /home/vagrant/.bashrc
fi

cd /home/vagrant || exit

cat << "EOT" >> .bashrc
eval "$(register-python-argcomplete bygg)"
EOT

cat << "EOT" >> .zshrc
export PATH="/home/vagrant/.local/bin:$PATH"
autoload -U bashcompinit ; bashcompinit
eval "$($(dirname $(readlink -f $(which bygg)))/register-python-argcomplete bygg)"
EOT


cd /home/vagrant/bygg || exit
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0.dev0 pipx install . --force
