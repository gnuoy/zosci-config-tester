# zosci-config-tester

## Description

At the moment this is limited to testing certain roles within zosci-config.
A full end-to-end run is not supported.

## Deployment

The charm can be deployed as a single unit in which case the ansible playbooks
are run on the same unit as the coordinator.

To avoid having two different charms (one for the coordinator and one for the
targets) this charm does both. This also allows the coordinator to be a
different ubuntu release from the target.

    juju deploy --channel edge --series focal zosci-config-tester coordinator
    juju deploy --force --channel edge --series xenial zosci-config-tester xenial-target
    juju add-relation coordinator:test-coordinator xenial-target:test-runner

or to use the bundle in the charm:

    juju deploy --force $(pwd)/bundle.yaml

Ansible can be run on any of the units which are bionic+ and which hosts ansible then
targets is controlled by `/root/branches/hosts`. Xenial can be used as a target
but not a coordinator. (zosci-config syntax seems to require a more recent
ansible version that the one shipped with xenial).

## Single node deployments

Edit `/root/branchesi/hosts` and uncomment 127.0.0.1

NOTE: At the moment this with be reverted by the charm

## Configuring what to run

Which roles are run is managed in `/root/branches/test-pb.yaml`. This playbook
has an additional role called `setup-test-env` which is specific to this test
runner and sets up test variables. This should be the first element
in the list of roles. After that add the roles to be tested. For example

    - hosts: all
      roles:
        - setup-test-env
        - handle-func-test-pr

This will setup the test PR then run `handle-func-test-pr` to apply
any func-test-pr directives to a downloaded PR.

The following roles have been tested:

- handle-func-test-pr
- prepare-package-environment
- charm-build

## Configuring test variables

Which PR is used for the tests, what commit message to parse etc is defined in
`/root/branches/setup-test-env/tasks/main.yaml`. The first entry in there is
"Set variables for test run". These can be edited as required.

It is possible to test a different commit message from that associate with the
PR. To do this add the desired commit message to
`/root/branches/test-commit-msg`

## Running Ansible

To run ansible:

    juju ssh coordinator/0
    sudo su -
    export ANSIBLE_ROLES_PATH=/root/branches/zuul-jobs/roles:/root/branches/zosci-config/roles/
    cd /root/branches
    ansible-playbook -i hosts test-pb.yaml
