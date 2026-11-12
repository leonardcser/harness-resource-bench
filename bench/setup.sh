#!/bin/sh
# Prepare a fresh Ubuntu VM for the benchmark, as the benchmark VM is set up:
# podman, tmux and uv, the cgroup controllers delegated to the user, and no
# automatic updates. Run it once, as the user who runs the benchmark
set -eu

if [ "$(nproc)" -lt 6 ]; then
  echo "The benchmark needs CPUs 0 to 5; this host has $(nproc)." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y podman tmux curl git

# Let the user's containers have their own CPUs, memory and process limits
sudo mkdir -p /etc/systemd/system/user@.service.d
printf '[Service]\nDelegate=cpu cpuset io memory pids\n' |
  sudo tee /etc/systemd/system/user@.service.d/delegate.conf >/dev/null
sudo systemctl daemon-reload

# Packages must not change during or between runs
printf 'APT::Periodic::%s "0";\n' Enable Update-Package-Lists \
  Unattended-Upgrade Download-Upgradeable-Packages AutocleanInterval |
  sudo tee /etc/apt/apt.conf.d/20auto-upgrades >/dev/null

command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh

echo "Done. Log out and in again, so that systemd delegates the controllers."
