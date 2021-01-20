def _get_instance_info(stack,hostname):

    _lookup = {"must_exists":True}
    _lookup["must_be_one"] = True
    _lookup["resource_type"] = "server"
    _lookup["hostname"] = hostname
    _lookup["region"] = stack.aws_default_region
    _info = list(stack.get_resource(**_lookup))[0]

    return _info["instance_id"]

def _get_ssh_key(stack):

    _lookup = {"must_exists":True}
    _lookup["resource_type"] = "ssh_key_pair"
    _lookup["name"] = stack.ssh_keyname
    _lookup["serialize"] = True
    _lookup["serialize_keys"] = [ "private_key" ]

    return stack.get_resource(decrypt=True,**_lookup)["private_key"]

def _get_private_ips_frm_hosts(hosts,stack):

    _lookup = {"must_exists":True,"must_be_one":True}
    _lookup["resource_type"] = "server"

    private_ips = []

    for host in stack.to_list(hosts):

        _lookup["hostname"] = host
        _host_info = list(stack.get_resource(**_lookup))[0]

        if _host_info["private_ip"] not in private_ips: 
            private_ips.append(_host_info["private_ip"])

    return ",".join(private_ips)

def run(stackargs):

    import json

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_required(key="bastion_hostname")
    stack.parse.add_required(key="kafka_cluster")
    stack.parse.add_required(key="ssh_keyname")
    stack.parse.add_required(key="aws_default_region")

    stack.parse.add_required(key="zookeeper_hosts")
    stack.parse.add_required(key="broker_hosts")
    stack.parse.add_required(key="schema_registry_hosts")
    stack.parse.add_required(key="connect_hosts")
    stack.parse.add_required(key="rest_hosts")
    stack.parse.add_required(key="ksql_hosts")
    stack.parse.add_required(key="control_center_hosts")

    stack.parse.add_optional(key="vm_username",default="ubuntu")
    stack.parse.add_optional(key="publish_creds",default=True,null_allowed=True)
    stack.parse.add_optional(key="use_docker",default=True,null_allowed=True)

    stack.parse.add_optional(key="terraform_docker_exec_env",default="elasticdev/terraform-run-env")
    stack.parse.add_optional(key="ansible_docker_exec_env",default="elasticdev/ansible-run-env")

    # Add host group
    stack.add_hostgroups("elasticdev:::ubuntu::18.04-docker","install_docker")
    stack.add_hostgroups("elasticdev:::ansible::ubuntu-18.04","install_python")
    stack.add_hostgroups("elasticdev:::kafka::ubuntu_vendor_setup","ubuntu_vendor_setup")
    stack.add_hostgroups("elasticdev:::kafka::ubuntu_vendor_init_cluster","ubuntu_vendor_init_cluster")

    # Initialize 
    stack.init_variables()
    stack.init_hostgroups()

    # install docker on bastion hosts
    inputargs = {"display":True}
    inputargs["human_description"] = "Install Docker on bastion {}".format(stack.bastion_hostname)
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.install_docker
    stack.add_groups_to_host(**inputargs)

    # get ssh_key
    private_key = _get_ssh_key(stack)

    # install with bastion hosts
    stateful_id = stack.random_id(size=10)

    base_env_vars = {"METHOD":"create"}
    base_env_vars["docker_exec_env".upper()] = stack.ansible_docker_exec_env
    base_env_vars["ANSIBLE_DIR"] = "/var/tmp/ansible"
    base_env_vars["STATEFUL_ID"] = stateful_id
    base_env_vars["ANS_VAR_private_key"] = private_key

    kafka_zookeeper_ips = _get_private_ips_frm_hosts(stack.zookeeper_hosts,stack)
    kafka_broker_ips = _get_private_ips_frm_hosts(stack.broker_hosts,stack)
    kafka_schema_registry_ips = _get_private_ips_frm_hosts(stack.schema_registry_hosts,stack)
    kafka_connect_ips = _get_private_ips_frm_hosts(stack.connect_hosts,stack)
    kafka_rest_ips = _get_private_ips_frm_hosts(stack.rest_hosts,stack)
    kafka_ksql_ips = _get_private_ips_frm_hosts(stack.ksql_hosts,stack)
    kafka_control_center_ips = _get_private_ips_frm_hosts(stack.control_center_hosts,stack)

    base_env_vars["ANS_VAR_kafka_zookeeper"] = kafka_zookeeper_ips
    base_env_vars["ANS_VAR_kafka_broker"] = kafka_broker_ips
    base_env_vars["ANS_VAR_kafka_schema_registry"] = kafka_schema_registry_ips
    base_env_vars["ANS_VAR_kafka_connect"] = kafka_connect_ips
    base_env_vars["ANS_VAR_kafka_rest"] = kafka_rest_ips
    base_env_vars["ANS_VAR_kafka_ksql"] = kafka_ksql_ips
    base_env_vars["ANS_VAR_kafka_control_center"] = kafka_control_center_ips

    ###############################################################
    # deploy Ansible files
    ###############################################################

    human_description = "Setting up Ansible"

    inputargs = {"display":True}
    inputargs["human_description"] = human_description
    inputargs["env_vars"] = json.dumps(base_env_vars.copy())
    inputargs["stateful_id"] = stateful_id
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.ubuntu_vendor_setup

    stack.add_groups_to_host(**inputargs)

    # install python hosts
    env_vars = {"METHOD":"create"}
    env_vars["STATEFUL_ID"] = stack.random_id(size=10)
    env_vars["ANS_VAR_private_key"] = private_key
    env_vars["ANS_VAR_exec_ymls"] = "entry_point/10-install-python.yml"
    env_vars["ANSIBLE_DIR"] = "/var/tmp/ansible"
    #env_vars["ANS_VAR_host_ips"] = ",".join(private_ips)

    inputargs = {"display":True}
    inputargs["human_description"] = 'Install Python for Ansible'
    inputargs["env_vars"] = json.dumps(env_vars)
    inputargs["stateful_id"] = env_vars["STATEFUL_ID"]
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.install_python

    stack.add_groups_to_host(**inputargs)

    # install prereq kafka
    human_description = "Prereq for Kafka"

    env_vars = base_env_vars.copy()
    env_vars["ANS_VAR_exec_ymls"] = "entry_point/20-prereq.yml"
    docker_env_fields_keys = env_vars.keys()
    env_vars["DOCKER_ENV_FIELDS"] = ",".join(docker_env_fields_keys)

    inputargs = {"display":True}
    inputargs["human_description"] = human_description
    inputargs["env_vars"] = json.dumps(env_vars)
    inputargs["stateful_id"] = stateful_id
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.ubuntu_vendor_init_cluster

    stack.add_groups_to_host(**inputargs)

    # install zookeeper kafka
    human_description = "Install zookeeper"
    env_vars = base_env_vars.copy()
    env_vars["ANS_VAR_exec_ymls"] = "entry_point/30-zookeeper.yml"
    docker_env_fields_keys = env_vars.keys()
    env_vars["DOCKER_ENV_FIELDS"] = ",".join(docker_env_fields_keys)

    inputargs = {"display":True}
    inputargs["human_description"] = human_description
    inputargs["env_vars"] = json.dumps(env_vars)
    inputargs["stateful_id"] = stateful_id
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.ubuntu_vendor_init_cluster

    stack.add_groups_to_host(**inputargs)

    # install broker kafka
    human_description = "Install broker"
    env_vars = base_env_vars.copy()
    env_vars["ANS_VAR_exec_ymls"] = "entry_point/40-broker.yml"
    docker_env_fields_keys = env_vars.keys()
    env_vars["DOCKER_ENV_FIELDS"] = ",".join(docker_env_fields_keys)

    inputargs = {"display":True}
    inputargs["human_description"] = human_description
    inputargs["env_vars"] = json.dumps(env_vars)
    inputargs["stateful_id"] = stateful_id
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.ubuntu_vendor_init_cluster

    stack.add_groups_to_host(**inputargs)

    # install schema kafka
    human_description = "Install schema"
    env_vars = base_env_vars.copy()
    env_vars["ANS_VAR_exec_ymls"] = "entry_point/50-schema.yml"
    docker_env_fields_keys = env_vars.keys()
    env_vars["DOCKER_ENV_FIELDS"] = ",".join(docker_env_fields_keys)

    inputargs = {"display":True}
    inputargs["human_description"] = human_description
    inputargs["env_vars"] = json.dumps(env_vars)
    inputargs["stateful_id"] = stateful_id
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.ubuntu_vendor_init_cluster

    stack.add_groups_to_host(**inputargs)

    # install connect kafka
    human_description = "Install connnect"
    env_vars = base_env_vars.copy()
    env_vars["ANS_VAR_exec_ymls"] = "entry_point/60-connect.yml"
    docker_env_fields_keys = env_vars.keys()
    env_vars["DOCKER_ENV_FIELDS"] = ",".join(docker_env_fields_keys)

    inputargs = {"display":True}
    inputargs["human_description"] = human_description
    inputargs["env_vars"] = json.dumps(env_vars)
    inputargs["stateful_id"] = stateful_id
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.ubuntu_vendor_init_cluster

    stack.add_groups_to_host(**inputargs)

    # install ksql kafka
    human_description = "Install ksql"
    env_vars = base_env_vars.copy()
    env_vars["ANS_VAR_exec_ymls"] = "entry_point/70-ksql.yml"
    docker_env_fields_keys = env_vars.keys()
    env_vars["DOCKER_ENV_FIELDS"] = ",".join(docker_env_fields_keys)

    inputargs = {"display":True}
    inputargs["human_description"] = human_description
    inputargs["env_vars"] = json.dumps(env_vars)
    inputargs["stateful_id"] = stateful_id
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.ubuntu_vendor_init_cluster

    stack.add_groups_to_host(**inputargs)

    # install rest kafka
    human_description = "Install rest"
    env_vars = base_env_vars.copy()
    env_vars["ANS_VAR_exec_ymls"] = "entry_point/80-rest.yml"
    docker_env_fields_keys = env_vars.keys()
    env_vars["DOCKER_ENV_FIELDS"] = ",".join(docker_env_fields_keys)

    inputargs = {"display":True}
    inputargs["human_description"] = human_description
    inputargs["env_vars"] = json.dumps(env_vars)
    inputargs["stateful_id"] = stateful_id
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.ubuntu_vendor_init_cluster

    stack.add_groups_to_host(**inputargs)

    # install control kafka
    human_description = "Install control"
    env_vars = base_env_vars.copy()
    env_vars["ANS_VAR_exec_ymls"] = "entry_point/90-control.yml"
    docker_env_fields_keys = env_vars.keys()
    env_vars["DOCKER_ENV_FIELDS"] = ",".join(docker_env_fields_keys)

    inputargs = {"display":True}
    inputargs["human_description"] = human_description
    inputargs["env_vars"] = json.dumps(env_vars)
    inputargs["stateful_id"] = stateful_id
    inputargs["automation_phase"] = "infrastructure"
    inputargs["hostname"] = stack.bastion_hostname
    inputargs["groups"] = stack.ubuntu_vendor_init_cluster

    stack.add_groups_to_host(**inputargs)

    ###############################################################
    # publish variables
    ###############################################################
    _publish_vars = {"kafka_cluster":stack.kafka_cluster}
    _publish_vars["kafka_zookeeper"] = kafka_zookeeper_ips
    _publish_vars["kafka_broker"] = kafka_broker_ips
    _publish_vars["kafka_schema_registry"] = kafka_schema_registry_ips
    _publish_vars["kafka_connect"] = kafka_connect_ips
    _publish_vars["kafka_rest"] = kafka_rest_ips
    _publish_vars["kafka_ksql"] = kafka_ksql_ips
    _publish_vars["kafka_control_center"] = kafka_control_center_ips
    stack.publish(_publish_vars)

    return stack.get_results()
