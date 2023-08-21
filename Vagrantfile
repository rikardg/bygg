# Simple Vagrant machines for testing in clean environments. Bygg is rsynced to /bygg in the VMs
# when the machines are started or reloaded (vagrant up and vagrant reload, respectively).

machines = [
  {
    :hostname => "fedora",
    :box => "fedora/38-cloud-base",
    :shellscript => <<-'SCRIPT'
      sudo dnf update -y
      sudo dnf install -y git pipx python3-pip neovim kitty-terminfo zsh
      cp /etc/skel/.zshrc /home/vagrant/.zshrc && chown vagrant:vagrant /home/vagrant/.zshrc && echo "export PATH=/home/vagrant/.local/bin:$PATH" >> /home/vagrant/.zshrc
      cp /etc/skel/.bashrc /home/vagrant/.bashrc && chown vagrant:vagrant /home/vagrant/.bashrc && echo "export PATH=/home/vagrant/.local/bin:$PATH" >> /home/vagrant/.bashrc
      SCRIPT
  },
  {
    :hostname => "debian",
    :box => "debian/bookworm64",
    :shellscript => <<-'SCRIPT'
      sudo apt update
      sudo apt dist-upgrade -y
      sudo apt install -y git pipx python3-pip python3-venv neovim kitty-terminfo zsh
      cp /etc/zsh/newuser.zshrc.recommended /home/vagrant/.zshrc && chown vagrant:vagrant /home/vagrant/.zshrc && echo "export PATH=/home/vagrant/.local/bin:$PATH" >> /home/vagrant/.zshrc
      cp /etc/skel/.bashrc /home/vagrant/.bashrc && chown vagrant:vagrant /home/vagrant/.bashrc && echo "export PATH=/home/vagrant/.local/bin:$PATH" >> /home/vagrant/.bashrc
      SCRIPT
  },
]

Vagrant.configure(2) do |config|
  config.vm.provider :libvirt do |libvirt|
    libvirt.cpus = 4
    libvirt.memory = 2048
  end

  machines.each do |machine|
    config.vm.define machine[:hostname] do |node|
      node.vm.synced_folder ".", "/vagrant", disabled: true
      node.vm.box = machine[:box]
      node.vm.hostname = machine[:hostname]
      node.vm.provision "shell",
        inline: machine[:shellscript]
      node.vm.synced_folder ".", "/bygg", type: "rsync"
    end
  end
end
