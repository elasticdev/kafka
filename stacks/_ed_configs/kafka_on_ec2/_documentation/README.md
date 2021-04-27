**Description**

  - The stack that creates a Kafka on Ec2 instances on AWS.

**Infrastructure**

  - expects ssh_keyname to be uploaded to Ec2
  - expects vpc and security groups to be already configured and loaded in ED

**Required**

| argument      | description                            | var type | default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| ssh_keyname   | the name the ssh_keyname to use for the VMs       | string   | None         |
| kafka_cluster   | the name of the kafka cluster       | string   | None         |
| num_of_zookeeper   | the name of the kafka cluster       | string   | 1         |
| num_of_broker   | the name of the kafka cluster       | string   | 1         |
| num_of_schema_registry   | the name of the kafka cluster       | string   | 1         |
| num_of_connect   | the name of the kafka cluster       | string   | 1         |
| num_of_rest   | the name of the kafka cluster       | string   | 1         |
| num_of_ksql   | the name of the kafka cluster       | string   | 1         |
| num_of_control_center   | the name of the kafka cluster       | string   | 1         |
| image   | the ami image used for the Kafka instances      | string   | ami-06fb5332e8e3e577a         |
| bastion_security_groups   | the security group used for the bastion config host      | string   | bastion         |
| bastion_subnet   | the subnet or subnet label used for the bastion config host      | string   | private         |
| bastion_image   | the ami image used for the bastion config host      | string   | ami-06fb5332e8e3e577a         |

**Optional**

| argument           | description                            | var type |  default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| aws_default_region   | aws region to create the ecr repo                | string   | us-east-1         |
| vm_username | The username for the VM.  e.g. ec2 for AWS linux     | string   | master       |
| security_groups | name of the security groups entered into ED resources to use for the VMs | string   | None       |
| vpc_name | name of the vpc entered into ED resources to use for the VMs | string   | None       |
| subnet | name of the subnet entered into ED resources to use for the VMs | string   | None       |
| instance_type | the VMs instance_type for the VMs | string   | None       |
| disksize | the disksize for the VM | string   | None       |
| tags | the tags for the Kafka cluster as ED resources | string   | None       |
| labels | the labels for the Kafka cluster as ED resources | string   | None       |

**Sample entry:**

```
infrastructure:
   kafka:
       stack_name: elasticdev:::kafka_on_ec2
       dependencies:
          - infrastructure::vpc
          - infrastructure::ssh_upload
       arguments:
          image: ami-03aad423811bbee56
          bastion_image: ami-03aad423811bbee56
          bastion_config_destroy: true
          bastion_security_groups: bastion
          bastion_subnet: public
          hostname_random: true
          size: t3.micro
          ssh_keyname: kafka-cluster-ssh-dev
          num_of_replicas: 5
          security_groups: database
          subnet: private
          disksize: 25
       credentials:
           - reference: aws_2
             orchestration: true
```







