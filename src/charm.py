#!/usr/bin/env python3
# Copyright 2022 Ubuntu
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

    https://discourse.charmhub.io/t/4208
"""

import logging

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus

import pathlib
import shutil
import subprocess

import interface_zosci_test_runner

logger = logging.getLogger(__name__)


class ZosciConfigTesterCharm(CharmBase):
    """Charm the service."""

    _stored = StoredState()
    ssh_priv_key = pathlib.Path("/root/.ssh/id_rsa")
    ssh_pub_key = pathlib.Path("/root/.ssh/id_rsa.pub")
    ssh_auth_keys = pathlib.Path("/root/.ssh/authorized_keys")
    ssh_known_hosts = pathlib.Path("/root/.ssh/known_hosts")
    ansible_hosts = pathlib.Path("/root/branches/hosts")

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.install, self._on_install)
        self._stored.set_default(things=[])
        self.runners = interface_zosci_test_runner.ZosciConfigRunners(
            self, "test-runner"
        )
        self.coordinators = interface_zosci_test_runner.ZosciConfigRunners(
            self, "test-coordinator"
        )
        self.framework.observe(self.runners.on.ready_runner, self._on_config_changed)
        self.framework.observe(
            self.coordinators.on.ready_runner, self._on_config_changed
        )

    def _on_install(self, _):
        cmd = ["apt", "install", "--yes", "ansible"]
        subprocess.check_output(cmd)

    def gen_ssh_keys(self):
        key_file = str(self.ssh_priv_key)
        cmd = ["ssh-keygen", "-t", "rsa", "-q", "-N", "", "-f", key_file]
        subprocess.check_output(cmd)

    def get_private_key(self):
        with open(str(self.ssh_priv_key), "r") as f:
            key = f.read()
        return key

    def get_public_key(self):
        with open(str(self.ssh_pub_key), "r") as f:
            key = f.read()
        return key

    def get_authorized_keys(self):
        with open(str(self.ssh_auth_keys), "r") as f:
            keys = f.read()
        return keys

    def announce_pub_key(self):
        pub_key = self.get_public_key()
        self.runners.set_conn_data(pub_key)
        self.coordinators.set_conn_data(pub_key)

    def get_remote_data(self):
        remote_keys = dict(
            self.runners.get_runner_info(), **self.coordinators.get_runner_info()
        )
        return remote_keys

    def update_authorized_keys(self):
        auth_keys = self.get_authorized_keys()
        new_keys = []
        new_keys.append(self.get_public_key())
        # for unit, data in self.runners.get_runner_info().items():
        for unit, data in self.get_remote_data().items():
            if data["pub_key"] not in auth_keys:
                new_keys.append(data["pub_key"])
        for key in new_keys:
            with open(str(self.ssh_auth_keys), "a") as f:
                f.write(key + "\n")

    def get_remote_ips(self):
        remote_data = self.get_remote_data()
        return [v["ip"] for v in remote_data.values() if v.get("ip")]

    def write_hosts(self):
        with open(str(self.ansible_hosts), "w") as f:
            f.write("[runners]\n")
            f.write("# 127.0.0.1\n")
            for i in self.get_remote_ips():
                f.write(i + "\n")

    def update_known_hosts(self):
        # Wipes the known_hosts which might not be ideal.
        ips = self.get_remote_ips()
        ips.append("127.0.0.1")
        with open(str(self.ssh_known_hosts), "wb") as f:
            for i in ips:
                out = subprocess.check_output(["ssh-keyscan", "-H", i])
                f.write(out)

    def _on_config_changed(self, _):
        """Just an example to show how to deal with changed configuration.
        """
        branch_dir = pathlib.Path("/root/branches")
        if not branch_dir.exists():
            subprocess.check_output(["rsync", "-a", "src/files/branches", "/root/"])
        charm_test_dir = pathlib.Path("/root/charm-test-dir")
        if not charm_test_dir.exists():
            charm_test_dir.mkdir()
        zosci_config_dir = pathlib.Path("/root/branches/zosci-config")
        if not zosci_config_dir.exists():
            cmd = [
                "git",
                "clone",
                "-b",
                self.config["zosci-config-branch"],
                self.config["zosci-config-repon"],
                str(zosci_config_dir),
            ]
            subprocess.check_output(cmd)
        zuul_jobs_dir = pathlib.Path("/root/branches/zuul-jobs")
        if not zuul_jobs_dir.exists():
            cmd = [
                "git",
                "clone",
                "-b",
                "master",
                "https://opendev.org/zuul/zuul-jobs.git",
                str(zuul_jobs_dir),
            ]
            subprocess.check_output(cmd)
        if not self.ssh_priv_key.exists():
            self.gen_ssh_keys()
        self.announce_pub_key()
        self.update_authorized_keys()
        self.write_hosts()
        self.update_known_hosts()
        return


if __name__ == "__main__":
    main(ZosciConfigTesterCharm)
