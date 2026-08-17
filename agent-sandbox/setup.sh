#!/usr/bin/env bash
# Arch Linux setup script mirroring cloud-init.yml
#
# To initialize the vm:
#   orb create arch -u agent-dev --isolated --forward-ssh-agent --mount ~/External:/mnt/projects my-sandbox
#   cat setup.sh | orb -m my-sandbox sudo bash
#
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo ./setup.sh)" >&2
  exit 1
fi

# 1. Install packages
pacman -Sy --needed --noconfirm \
  tailscale \
  mosh \
  openssh \
  neovim \
  kitty-terminfo \
  fnm \
  git \
  go \
  python \
  python-uv \
  fzf

# 2. Generate the en_US.UTF-8 locale to prevent terminal warnings
sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf

# 3. Enable and start the OpenSSH and Tailscale servers
systemctl enable --now sshd
systemctl enable --now tailscaled

# 4. Figure out which user to install into
MAC_USER="${MAC_USER:-$(ls /home | head -n 1)}"
if [[ -z "$MAC_USER" ]]; then
  echo "No user found under /home; set MAC_USER=<name> and rerun" >&2
  exit 1
fi
echo "Installing user tooling for: $MAC_USER"

# 5. Install herdr + omp as the standard user so it goes to their ~/.local/bin
su - "$MAC_USER" -c 'curl -fsSL https://herdr.dev/install.sh | sh'
su - "$MAC_USER" -c 'curl -fsSL https://omp.sh/install | sh'

# 6. Add ~/.local/bin to the user's Bash PATH for herdr and local tools
echo 'export PATH="$HOME/.local/bin:$PATH"' >> "/home/$MAC_USER/.bashrc"
echo 'eval "$(fnm env --use-on-cd --shell bash)"' >> "/home/$MAC_USER/.bashrc"

# 7. Pre-approve github ssh key
mkdir -p "/home/$MAC_USER/.ssh"
ssh-keyscan github.com > /home/$MAC_USER/.ssh/known_hosts 2>/dev/null
# Uncomment to inject a public key (e.g. for Moshi/iPhone) into authorized_keys:
# echo "ssh-ed25519 AAAAC3NzaC... YOUR_MOSHI_PUBLIC_KEY" >> "/home/$MAC_USER/.ssh/authorized_keys"
chown -R "$MAC_USER:$MAC_USER" "/home/$MAC_USER/.ssh"
chmod 700 "/home/$MAC_USER/.ssh"
chmod 600 "/home/$MAC_USER/.ssh/authorized_keys"

# 8. Clone configuration
su - "$MAC_USER" -c 'git clone git@github.com:f1code/skills.git ~/.agents'
su - "$MAC_USER" -c 'mkdir ~/.omp && ln -s ~/.agents/agent-config/omp ~/.omp/agent'

echo "Done. Manual step remaining: join your Tailnet with"
echo "  tailscale up --authkey=tskey-auth-YOUR_KEY_HERE"
