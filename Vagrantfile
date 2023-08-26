# Simple Vagrant machines for testing in clean environments. Bygg is rsynced to /bygg in the VMs
# when the machines are started or reloaded (vagrant up and vagrant reload, respectively).

machines = [
  {
    :hostname => "fedora",
    :box => "fedora/38-cloud-base",
  },
  {
    :hostname => "debian",
    :box => "debian/bookworm64",
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
        path: "Vagrantsetup.sh",
        privileged: false
      node.vm.synced_folder ".", "/home/vagrant/bygg", type: "rsync"
    end
  end
end
