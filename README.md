# Ansible Automation Platform Configuration as Code examples template

This is a combination of all the Red Hat CoP Config as Code collections to deploy and configure Network tools. This is built for multi tools and endpoints (meaning multiple network-brands instances). 

[^1]: If you only have/want one environment you could delete dev/test/prod/corp/mgm/pre-prod/lab folders in group_vars and remove all the _all added to vars in all group. Also if you want to have each team/group maintain their own org/code in their own repo, see the repo_per_org branch.

You will need to replace the vault files with your own with these variables:

```yaml
---
snmp_pollers:
  - name: "Entuity"
    snmpv3_user: "User for snmp service"
    snmpv3_auth_password: "Authpassword"
    snmpv3_encryption_method: "AES-256"
    snmpv3_priv_password: "Privpassword"
    snmpv3_auth_method: "MD5"
    snmpv2c_community: “community-pwd”
...
```

**_NOTE:_** Do not forget to update your inventory files replacing the `HERE` lines, if you do not have a `builder` server you can use `hub` for this. Also update `scm_url` in `group_vars/all/projects.yml` with your git URL.


## Requirements

The awx.awx or ansible.controller collections MUST be installed in order for this collection to work. It is recommended they be invoked in the playbook in the following way.

```yaml
---
- name: Playbook to configure ansible controller post installation
  hosts: localhost
  connection: local
  vars:
    controller_validate_certs: false
  collections:
    - cisco.nxos.nxos_snmp_server module
```

## Links to Ansible Automation Platform Collections

|                                      Collection Name                                         |                 Purpose                  |
|:--------------------------------------------------------------------------------------------:|:----------------------------------------:|
| [cisco.nxos.nxos_snmp_server module](https://docs.ansible.com/ansible/latest/collections/cisco/nxos/nxos_snmp_server_module.html) |   SNMP Server resource module modules          |

## Links to other Validated Configuration Collections for Ansible Automation Platform

|                                      Collection Name                                       |                 Purpose                  |
|:------------------------------------------------------------------------------------------:|:----------------------------------------:|
|  |      |

## SNMP automation

`ansible-playbook -i inventory_dev.yml -l dev playbooks/snmp_automation.yml --tags snmp --limit dev --ask-vault-pass -e "env=[dev]"`


## custom ee

currently doesn't work in CLI, expected to be run in Controller

## custom collections

currently doesn't work in CLI, expected to be run in Controller

