FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Remove Yarn repository to avoid expired GPG key (NO_PUBKEY 62D54FD4003F6525)
RUN rm -f /etc/apt/sources.list.d/yarn.list