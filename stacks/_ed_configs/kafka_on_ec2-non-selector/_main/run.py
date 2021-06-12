def _vm_create(server_type,num,stack):

    default_values = {"keyname":stack.ssh_keyname}
    default_values["image"] = stack.image
    default_values["aws_default_region"] = stack.aws_default_region
    default_values["security_groups"] = stack.security_groups
    default_values["vpc_name"] = stack.vpc_name
    default_values["subnet"] = stack.subnet
    default_values["size"] = stack.instance_type
    default_values["disksize"] = stack.disksize
    default_values["register_to_ed"] = None

    hosts = []

    # Create ec2 instances
    for num in range(int(num)):

        hostname = "{}-{}-num-{}".format(stack.hostname_base,server_type,num).replace("_","-")
        hosts.append(hostname)

        default_values["hostname"] = hostname

        inputargs = {"default_values":default_values}
        human_description = "Creating hostname {} on ec2".format(hostname)

        inputargs["automation_phase"] = "infrastructure"
        inputargs["human_description"] = human_description
        stack.ec2_ubuntu.insert(display=True,**inputargs)

    return hosts

def run(stackargs):

    # instantiate authoring stack
    stack = newStack(stackargs)

    # Add default variables
    stack.parse.add_required(key="ssh_keyname")

    stack.parse.add_required(key="kafka_cluster")
    stack.parse.add_required(key="num_of_zookeeper",default=1)
    stack.parse.add_required(key="num_of_broker",default=1)
    stack.parse.add_required(key="num_of_schema_registry",default=1)
    stack.parse.add_required(key="num_of_connect",default=1)
    stack.parse.add_required(key="num_of_rest",default=1)
    stack.parse.add_required(key="num_of_ksql",default=1)
    stack.parse.add_required(key="num_of_control_center",default=1)
    stack.parse.add_required(key="image",default="ami-06fb5332e8e3e577a")

    stack.parse.add_optional(key="vm_username",default="null")

    # bastion configs
    # guysguys
    stack.parse.add_optional(key="bastion_security_groups",default="bastion")
    stack.parse.add_optional(key="bastion_subnet",default="private")
    stack.parse.add_optional(key="bastion_image",default="ami-06fb5332e8e3e577a")
    stack.parse.add_optional(key="bastion_config_destroy",default="null")  # destroy bastion config

    stack.parse.add_optional(key="aws_default_region",default="us-east-1")
    stack.parse.add_optional(key="security_groups",default="null")
    stack.parse.add_optional(key="vpc_name",default="null")
    stack.parse.add_optional(key="subnet",default="null")
    stack.parse.add_optional(key="instance_type",default="t3.micro")
    stack.parse.add_optional(key="disksize",default="20")
    stack.parse.add_optional(key="ip_key",default="private_ip")

    stack.parse.add_optional(key="tags",default="null")
    stack.parse.add_optional(key="labels",default="null")

    # Add substack
    stack.add_substack('elasticdev:::ec2_ubuntu')
    stack.add_substack('elasticdev:::_kafka_cluster_on_ubuntu_by_bastion')

    # Initialize 
    stack.init_variables()
    stack.init_substacks()

    stack.set_parallel()

    # Set up basic hostnames
    stack.set_variable("hostname_base","{}-{}".format(stack.kafka_cluster,stack.random_id(size=3).lower()))
    stack.set_variable("bastion_hostname","{}-config".format(stack.hostname_base))

    # Set up bastion
    default_values = {"vpc_name":stack.vpc_name}
    default_values["keyname"] = stack.ssh_keyname
    default_values["aws_default_region"] = stack.aws_default_region
    default_values["size"] = stack.instance_type # we just ned a small machine for configuration
    default_values["disksize"] = 50 # we just set the disksize relatively large

    overide_values = {"hostname":stack.bastion_hostname}
    overide_values["register_to_ed"] = True
    overide_values["subnet"] = stack.bastion_subnet
    overide_values["security_groups"] = stack.bastion_security_groups
    overide_values["image"] = stack.bastion_image

    inputargs = {"default_values":default_values,
                 "overide_values":overide_values}

    human_description = "Creating bastion config hostname {} on ec2".format(stack.bastion_hostname)
    inputargs["automation_phase"] = "infrastructure"
    inputargs["human_description"] = human_description
    stack.ec2_ubuntu.insert(display=True,**inputargs)

    stack.parse.add_required(key="num_of_zookeeper",default=1)
    stack.parse.add_required(key="num_of_broker",default=1)
    stack.parse.add_required(key="num_of_schema_registry",default=1)
    stack.parse.add_required(key="num_of_connect",default=1)
    stack.parse.add_required(key="num_of_rest",default=1)
    stack.parse.add_required(key="num_of_ksql",default=1)
    stack.parse.add_required(key="num_of_control_center",default=1)

    zookeeper_hosts = _vm_create("zookeeper",stack.num_of_zookeeper,stack)
    broker_hosts = _vm_create("broker",stack.num_of_broker,stack)
    schema_registry_hosts = _vm_create("schema_registry",stack.num_of_schema_registry,stack)
    connect_hosts = _vm_create("connect",stack.num_of_connect,stack)
    rest_hosts = _vm_create("rest",stack.num_of_rest,stack)
    ksql_hosts = _vm_create("ksql",stack.num_of_ksql,stack)
    control_center_hosts = _vm_create("control_center",stack.num_of_control_center,stack)

    stack.unset_parallel(wait_all=True)

    default_values = {"kafka_cluster":stack.kafka_cluster}
    default_values["ssh_keyname"] = stack.ssh_keyname
    default_values["zookeeper_hosts"] = zookeeper_hosts
    default_values["broker_hosts"] = broker_hosts
    default_values["schema_registry_hosts"] = schema_registry_hosts
    default_values["connect_hosts"] = connect_hosts
    default_values["rest_hosts"] = rest_hosts
    default_values["ksql_hosts"] = ksql_hosts
    default_values["control_center_hosts"] = control_center_hosts
    default_values["aws_default_region"] = stack.aws_default_region
    if stack.vm_username: default_values["vm_username"] = stack.vm_username

    default_values["bastion_hostname"] = stack.bastion_hostname

    inputargs = {"default_values":default_values}
    inputargs["automation_phase"] = "infrastructure"
    inputargs["human_description"] = human_description
    stack._kafka_cluster_on_ubuntu_by_bastion.insert(display=True,**inputargs)

    #zookeeper_hosts
    #broker_hosts
    #schema_registry_hosts
    #connect_hosts
    #rest_hosts
    #ksql_hosts
    #control_center_hosts

    return stack.get_results()
