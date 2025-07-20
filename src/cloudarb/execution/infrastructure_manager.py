"""
Infrastructure execution manager for CloudArb.
Handles actual deployment and management of GPU workloads across cloud providers.
"""

import logging
import asyncio
import json
import subprocess
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import yaml
import kubernetes
from kubernetes import client, config
import boto3
from google.cloud import compute_v1
from azure.mgmt.compute import ComputeManagementClient
from azure.identity import DefaultAzureCredential

from ..config import get_settings
from ..models.workloads import Workload, WorkloadStatus
from ..monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)
settings = get_settings()


class TerraformManager:
    """Manages Terraform infrastructure provisioning."""

    def __init__(self):
        self.terraform_path = "/usr/local/bin/terraform"
        self.working_dir = "/tmp/cloudarb-terraform"
        self.state_file = f"{self.working_dir}/terraform.tfstate"
        self.ensure_working_dir()

    def ensure_working_dir(self):
        """Ensure Terraform working directory exists."""
        os.makedirs(self.working_dir, exist_ok=True)

    async def create_infrastructure(self, workload: Workload,
                                  allocation: Dict[str, Any]) -> Dict[str, Any]:
        """Create infrastructure for a workload using Terraform."""
        try:
            # Generate Terraform configuration
            tf_config = self._generate_terraform_config(workload, allocation)

            # Write Terraform files
            await self._write_terraform_files(tf_config)

            # Initialize Terraform
            init_result = await self._run_terraform_command(["init"])
            if init_result["success"] is False:
                return {"success": False, "error": f"Terraform init failed: {init_result['error']}"}

            # Plan Terraform
            plan_result = await self._run_terraform_command(["plan", "-out=tfplan"])
            if plan_result["success"] is False:
                return {"success": False, "error": f"Terraform plan failed: {plan_result['error']}"}

            # Apply Terraform
            apply_result = await self._run_terraform_command(["apply", "tfplan"])
            if apply_result["success"] is False:
                return {"success": False, "error": f"Terraform apply failed: {apply_result['error']}"}

            # Get outputs
            outputs = await self._get_terraform_outputs()

            return {
                "success": True,
                "infrastructure_id": outputs.get("infrastructure_id"),
                "instance_ids": outputs.get("instance_ids", []),
                "public_ips": outputs.get("public_ips", []),
                "private_ips": outputs.get("private_ips", []),
                "ssh_key_path": outputs.get("ssh_key_path"),
                "terraform_state": self.state_file
            }

        except Exception as e:
            logger.error(f"Error creating infrastructure: {e}")
            return {"success": False, "error": str(e)}

    async def destroy_infrastructure(self, infrastructure_id: str) -> Dict[str, Any]:
        """Destroy infrastructure using Terraform."""
        try:
            # Check if state file exists
            if not os.path.exists(self.state_file):
                return {"success": False, "error": "No Terraform state found"}

            # Destroy infrastructure
            destroy_result = await self._run_terraform_command(["destroy", "-auto-approve"])

            return {
                "success": destroy_result["success"],
                "error": destroy_result.get("error")
            }

        except Exception as e:
            logger.error(f"Error destroying infrastructure: {e}")
            return {"success": False, "error": str(e)}

    def _generate_terraform_config(self, workload: Workload,
                                 allocation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Terraform configuration for the workload."""
        provider = allocation.get("provider", "aws")
        instance_type = allocation.get("instance_type", "g4dn.xlarge")
        region = allocation.get("region", "us-east-1")
        gpu_count = allocation.get("gpu_count", 1)

        if provider == "aws":
            return self._generate_aws_config(workload, allocation)
        elif provider == "gcp":
            return self._generate_gcp_config(workload, allocation)
        elif provider == "azure":
            return self._generate_azure_config(workload, allocation)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _generate_aws_config(self, workload: Workload,
                           allocation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AWS Terraform configuration."""
        instance_type = allocation.get("instance_type", "g4dn.xlarge")
        region = allocation.get("region", "us-east-1")
        gpu_count = allocation.get("gpu_count", 1)

        return {
            "main.tf": f"""
terraform {{
  required_version = ">= 1.0"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = "{region}"
}}

# VPC and networking
resource "aws_vpc" "cloudarb_vpc" {{
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true

  tags = {{
    Name = "cloudarb-vpc-{workload.id}"
  }}
}}

resource "aws_subnet" "cloudarb_subnet" {{
  vpc_id = aws_vpc.cloudarb_vpc.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "{region}a"

  tags = {{
    Name = "cloudarb-subnet-{workload.id}"
  }}
}}

resource "aws_internet_gateway" "cloudarb_igw" {{
  vpc_id = aws_vpc.cloudarb_vpc.id

  tags = {{
    Name = "cloudarb-igw-{workload.id}"
  }}
}}

resource "aws_route_table" "cloudarb_rt" {{
  vpc_id = aws_vpc.cloudarb_vpc.id

  route {{
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.cloudarb_igw.id
  }}

  tags = {{
    Name = "cloudarb-rt-{workload.id}"
  }}
}}

resource "aws_route_table_association" "cloudarb_rta" {{
  subnet_id = aws_subnet.cloudarb_subnet.id
  route_table_id = aws_route_table.cloudarb_rt.id
}}

# Security group
resource "aws_security_group" "cloudarb_sg" {{
  name = "cloudarb-sg-{workload.id}"
  description = "Security group for CloudArb GPU instances"
  vpc_id = aws_vpc.cloudarb_vpc.id

  ingress {{
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  ingress {{
    from_port = 80
    to_port = 80
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  ingress {{
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  egress {{
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}
}}

# Key pair
resource "aws_key_pair" "cloudarb_key" {{
  key_name = "cloudarb-key-{workload.id}"
  public_key = file("${{path.module}}/ssh_key.pub")
}}

# GPU instance
resource "aws_instance" "gpu_instance" {{
  ami = "ami-0c7217cdde317cfec"  # Deep Learning AMI with CUDA
  instance_type = "{instance_type}"
  key_name = aws_key_pair.cloudarb_key.key_name
  vpc_security_group_ids = [aws_security_group.cloudarb_sg.id]
  subnet_id = aws_subnet.cloudarb_subnet.id
  associate_public_ip_address = true

  root_block_device {{
    volume_size = 100
    volume_type = "gp3"
  }}

  user_data = <<-EOF
              #!/bin/bash
              # Install Docker
              yum update -y
              yum install -y docker
              systemctl start docker
              systemctl enable docker

              # Install NVIDIA Docker
              distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
              curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
              curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.repo | sudo tee /etc/yum.repos.d/nvidia-docker.repo
              yum install -y nvidia-docker2
              systemctl restart docker

              # Run workload container
              docker run -d --gpus all \\
                --name cloudarb-workload-{workload.id} \\
                -p 80:80 \\
                -p 8888:8888 \\
                {workload.container_image or "nvidia/cuda:11.8-base-ubuntu20.04"}
              EOF

  tags = {{
    Name = "cloudarb-gpu-{workload.id}"
    WorkloadId = "{workload.id}"
    Provider = "aws"
  }}
}}

# Outputs
output "instance_id" {{
  value = aws_instance.gpu_instance.id
}}

output "public_ip" {{
  value = aws_instance.gpu_instance.public_ip
}}

output "private_ip" {{
  value = aws_instance.gpu_instance.private_ip
}}

output "ssh_key_path" {{
  value = "${{path.module}}/ssh_key"
}}
""",
            "variables.tf": """
variable "aws_region" {
  description = "AWS region"
  type = string
  default = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type = string
  default = "g4dn.xlarge"
}
""",
            "outputs.tf": """
output "infrastructure_id" {
  description = "Infrastructure ID"
  value = aws_instance.gpu_instance.id
}

output "instance_ids" {
  description = "Instance IDs"
  value = [aws_instance.gpu_instance.id]
}

output "public_ips" {
  description = "Public IPs"
  value = [aws_instance.gpu_instance.public_ip]
}

output "private_ips" {
  description = "Private IPs"
  value = [aws_instance.gpu_instance.private_ip]
}

output "ssh_key_path" {
  description = "SSH key path"
  value = "${path.module}/ssh_key"
}
"""
        }

    def _generate_gcp_config(self, workload: Workload,
                           allocation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate GCP Terraform configuration."""
        instance_type = allocation.get("instance_type", "n1-standard-4")
        region = allocation.get("region", "us-central1")
        gpu_type = allocation.get("gpu_type", "nvidia-tesla-t4")

        return {
            "main.tf": f"""
terraform {{
  required_version = ">= 1.0"
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 4.0"
    }}
  }}
}}

provider "google" {{
  project = "{settings.cloud_providers.gcp_project_id}"
  region = "{region}"
}}

# VPC network
resource "google_compute_network" "cloudarb_network" {{
  name = "cloudarb-network-{workload.id}"
  auto_create_subnetworks = false
}}

resource "google_compute_subnetwork" "cloudarb_subnet" {{
  name = "cloudarb-subnet-{workload.id}"
  ip_cidr_range = "10.0.1.0/24"
  network = google_compute_network.cloudarb_network.id
  region = "{region}"
}}

# Firewall rules
resource "google_compute_firewall" "cloudarb_firewall" {{
  name = "cloudarb-firewall-{workload.id}"
  network = google_compute_network.cloudarb_network.id

  allow {{
    protocol = "tcp"
    ports = ["22", "80", "443", "8888"]
  }}

  source_ranges = ["0.0.0.0/0"]
}}

# GPU instance
resource "google_compute_instance" "gpu_instance" {{
  name = "cloudarb-gpu-{workload.id}"
  machine_type = "{instance_type}"
  zone = "{region}-a"

  boot_disk {{
    initialize_params {{
      image = "debian-cloud/debian-11"
      size = 100
    }}
  }}

  network_interface {{
    network = google_compute_network.cloudarb_network.id
    subnetwork = google_compute_subnetwork.cloudarb_subnet.id
    access_config {{
      // Ephemeral public IP
    }}
  }}

  guest_accelerator {{
    type = "{gpu_type}"
    count = {allocation.get("gpu_count", 1)}
  }}

  scheduling {{
    on_host_maintenance = "TERMINATE"
  }}

  metadata = {{
    ssh-keys = "cloudarb:${{file("${{path.module}}/ssh_key.pub")}}"
  }}

  metadata_startup_script = <<-EOF
    # Install Docker
    apt-get update
    apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker

    # Install NVIDIA Docker
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list
    apt-get update
    apt-get install -y nvidia-docker2
    systemctl restart docker

    # Run workload container
    docker run -d --gpus all \\
      --name cloudarb-workload-{workload.id} \\
      -p 80:80 \\
      -p 8888:8888 \\
      {workload.container_image or "nvidia/cuda:11.8-base-ubuntu20.04"}
  EOF

  tags = ["cloudarb", "gpu", "workload-{workload.id}"]
}}

# Outputs
output "instance_id" {{
  value = google_compute_instance.gpu_instance.id
}}

output "public_ip" {{
  value = google_compute_instance.gpu_instance.network_interface[0].access_config[0].nat_ip
}}

output "private_ip" {{
  value = google_compute_instance.gpu_instance.network_interface[0].network_ip
}}
"""
        }

    def _generate_azure_config(self, workload: Workload,
                             allocation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Azure Terraform configuration."""
        instance_type = allocation.get("instance_type", "Standard_NC6")
        region = allocation.get("region", "eastus")

        return {
            "main.tf": f"""
terraform {{
  required_version = ">= 1.0"
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }}
  }}
}}

provider "azurerm" {{
  features {{}}
}}

# Resource group
resource "azurerm_resource_group" "cloudarb_rg" {{
  name = "cloudarb-rg-{workload.id}"
  location = "{region}"
}}

# Virtual network
resource "azurerm_virtual_network" "cloudarb_vnet" {{
  name = "cloudarb-vnet-{workload.id}"
  address_space = ["10.0.0.0/16"]
  location = azurerm_resource_group.cloudarb_rg.location
  resource_group_name = azurerm_resource_group.cloudarb_rg.name
}}

resource "azurerm_subnet" "cloudarb_subnet" {{
  name = "cloudarb-subnet-{workload.id}"
  resource_group_name = azurerm_resource_group.cloudarb_rg.name
  virtual_network_name = azurerm_virtual_network.cloudarb_vnet.name
  address_prefixes = ["10.0.1.0/24"]
}}

# Public IP
resource "azurerm_public_ip" "cloudarb_pip" {{
  name = "cloudarb-pip-{workload.id}"
  location = azurerm_resource_group.cloudarb_rg.location
  resource_group_name = azurerm_resource_group.cloudarb_rg.name
  allocation_method = "Dynamic"
}}

# Network interface
resource "azurerm_network_interface" "cloudarb_nic" {{
  name = "cloudarb-nic-{workload.id}"
  location = azurerm_resource_group.cloudarb_rg.location
  resource_group_name = azurerm_resource_group.cloudarb_rg.name

  ip_configuration {{
    name = "internal"
    subnet_id = azurerm_subnet.cloudarb_subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id = azurerm_public_ip.cloudarb_pip.id
  }}
}}

# Network security group
resource "azurerm_network_security_group" "cloudarb_nsg" {{
  name = "cloudarb-nsg-{workload.id}"
  location = azurerm_resource_group.cloudarb_rg.location
  resource_group_name = azurerm_resource_group.cloudarb_rg.name

  security_rule {{
    name = "SSH"
    priority = 1001
    direction = "Inbound"
    access = "Allow"
    protocol = "Tcp"
    source_port_range = "*"
    destination_port_range = "22"
    source_address_prefix = "*"
    destination_address_prefix = "*"
  }}

  security_rule {{
    name = "HTTP"
    priority = 1002
    direction = "Inbound"
    access = "Allow"
    protocol = "Tcp"
    source_port_range = "*"
    destination_port_range = "80"
    source_address_prefix = "*"
    destination_address_prefix = "*"
  }}

  security_rule {{
    name = "HTTPS"
    priority = 1003
    direction = "Inbound"
    access = "Allow"
    protocol = "Tcp"
    source_port_range = "*"
    destination_port_range = "443"
    source_address_prefix = "*"
    destination_address_prefix = "*"
  }}
}}

# GPU VM
resource "azurerm_linux_virtual_machine" "gpu_vm" {{
  name = "cloudarb-gpu-{workload.id}"
  resource_group_name = azurerm_resource_group.cloudarb_rg.name
  location = azurerm_resource_group.cloudarb_rg.location
  size = "{instance_type}"
  admin_username = "cloudarb"

  network_interface_ids = [
    azurerm_network_interface.cloudarb_nic.id
  ]

  admin_ssh_key {{
    username = "cloudarb"
    public_key = file("${{path.module}}/ssh_key.pub")
  }}

  os_disk {{
    caching = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb = 100
  }}

  source_image_reference {{
    publisher = "Canonical"
    offer = "UbuntuServer"
    sku = "18.04-LTS"
    version = "latest"
  }}

  custom_data = base64encode(<<-EOF
    #!/bin/bash
    # Install Docker
    apt-get update
    apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker

    # Install NVIDIA Docker
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list
    apt-get update
    apt-get install -y nvidia-docker2
    systemctl restart docker

    # Run workload container
    docker run -d --gpus all \\
      --name cloudarb-workload-{workload.id} \\
      -p 80:80 \\
      -p 8888:8888 \\
      {workload.container_image or "nvidia/cuda:11.8-base-ubuntu20.04"}
  EOF
  )

  tags = {{
    WorkloadId = "{workload.id}"
    Provider = "azure"
  }}
}}

# Outputs
output "instance_id" {{
  value = azurerm_linux_virtual_machine.gpu_vm.id
}}

output "public_ip" {{
  value = azurerm_public_ip.cloudarb_pip.ip_address
}}

output "private_ip" {{
  value = azurerm_network_interface.cloudarb_nic.private_ip_address
}}
"""
        }

    async def _write_terraform_files(self, config: Dict[str, str]):
        """Write Terraform configuration files."""
        for filename, content in config.items():
            filepath = os.path.join(self.working_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)

        # Generate SSH key pair
        ssh_key_path = os.path.join(self.working_dir, "ssh_key")
        ssh_pub_path = os.path.join(self.working_dir, "ssh_key.pub")

        # Generate SSH key (simplified - in production use proper key generation)
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096", "-f", ssh_key_path,
            "-N", "", "-C", "cloudarb@terraform"
        ], check=True)

    async def _run_terraform_command(self, args: List[str]) -> Dict[str, Any]:
        """Run Terraform command."""
        try:
            cmd = [self.terraform_path] + args
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "error": stderr.decode() if process.returncode != 0 else None
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_terraform_outputs(self) -> Dict[str, Any]:
        """Get Terraform outputs."""
        try:
            result = await self._run_terraform_command(["output", "-json"])
            if result["success"]:
                return json.loads(result["stdout"])
            return {}
        except Exception as e:
            logger.error(f"Error getting Terraform outputs: {e}")
            return {}


class KubernetesManager:
    """Manages Kubernetes workload deployment."""

    def __init__(self):
        self.kubeconfig_path = None
        self.api_client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Kubernetes client."""
        try:
            # Try to load in-cluster config first
            try:
                config.load_incluster_config()
                logger.info("Using in-cluster Kubernetes configuration")
            except:
                # Try to load kubeconfig file
                kubeconfig = os.getenv('KUBECONFIG', '~/.kube/config')
                config.load_kube_config(config_file=os.path.expanduser(kubeconfig))
                logger.info(f"Using kubeconfig: {kubeconfig}")

            self.api_client = client.ApiClient()

        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")

    async def deploy_workload(self, workload: Workload,
                            allocation: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy workload to Kubernetes cluster."""
        try:
            if not self.api_client:
                return {"success": False, "error": "Kubernetes client not initialized"}

            # Create namespace
            namespace = f"cloudarb-{workload.id}"
            await self._create_namespace(namespace)

            # Create GPU workload deployment
            deployment_result = await self._create_gpu_deployment(workload, allocation, namespace)

            # Create service
            service_result = await self._create_service(workload, namespace)

            # Create ingress (if needed)
            ingress_result = await self._create_ingress(workload, namespace)

            return {
                "success": True,
                "namespace": namespace,
                "deployment": deployment_result,
                "service": service_result,
                "ingress": ingress_result
            }

        except Exception as e:
            logger.error(f"Error deploying workload to Kubernetes: {e}")
            return {"success": False, "error": str(e)}

    async def _create_namespace(self, namespace: str) -> bool:
        """Create Kubernetes namespace."""
        try:
            v1 = client.CoreV1Api(self.api_client)

            # Check if namespace exists
            try:
                v1.read_namespace(namespace)
                return True
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    # Create namespace
                    ns = client.V1Namespace(
                        metadata=client.V1ObjectMeta(name=namespace)
                    )
                    v1.create_namespace(ns)
                    return True
                else:
                    raise

        except Exception as e:
            logger.error(f"Error creating namespace: {e}")
            return False

    async def _create_gpu_deployment(self, workload: Workload,
                                   allocation: Dict[str, Any],
                                   namespace: str) -> Dict[str, Any]:
        """Create GPU deployment."""
        try:
            apps_v1 = client.AppsV1Api(self.api_client)

            # Create deployment
            deployment = client.V1Deployment(
                metadata=client.V1ObjectMeta(
                    name=f"gpu-workload-{workload.id}",
                    namespace=namespace
                ),
                spec=client.V1DeploymentSpec(
                    replicas=1,
                    selector=client.V1LabelSelector(
                        match_labels={"app": f"gpu-workload-{workload.id}"}
                    ),
                    template=client.V1PodTemplateSpec(
                        metadata=client.V1ObjectMeta(
                            labels={"app": f"gpu-workload-{workload.id}"}
                        ),
                        spec=client.V1PodSpec(
                            containers=[
                                client.V1Container(
                                    name="gpu-container",
                                    image=workload.container_image or "nvidia/cuda:11.8-base-ubuntu20.04",
                                    ports=[
                                        client.V1ContainerPort(container_port=80),
                                        client.V1ContainerPort(container_port=8888)
                                    ],
                                    resources=client.V1ResourceRequirements(
                                        limits={
                                            "nvidia.com/gpu": allocation.get("gpu_count", 1)
                                        }
                                    ),
                                    env=[
                                        client.V1EnvVar(
                                            name="WORKLOAD_ID",
                                            value=str(workload.id)
                                        )
                                    ]
                                )
                            ],
                            restart_policy="Always"
                        )
                    )
                )
            )

            result = apps_v1.create_namespaced_deployment(
                namespace=namespace,
                body=deployment
            )

            return {
                "name": result.metadata.name,
                "uid": result.metadata.uid,
                "replicas": result.spec.replicas
            }

        except Exception as e:
            logger.error(f"Error creating GPU deployment: {e}")
            return {"error": str(e)}

    async def _create_service(self, workload: Workload, namespace: str) -> Dict[str, Any]:
        """Create Kubernetes service."""
        try:
            v1 = client.CoreV1Api(self.api_client)

            service = client.V1Service(
                metadata=client.V1ObjectMeta(
                    name=f"gpu-service-{workload.id}",
                    namespace=namespace
                ),
                spec=client.V1ServiceSpec(
                    selector={"app": f"gpu-workload-{workload.id}"},
                    ports=[
                        client.V1ServicePort(
                            port=80,
                            target_port=80,
                            name="http"
                        ),
                        client.V1ServicePort(
                            port=8888,
                            target_port=8888,
                            name="jupyter"
                        )
                    ],
                    type="LoadBalancer"
                )
            )

            result = v1.create_namespaced_service(
                namespace=namespace,
                body=service
            )

            return {
                "name": result.metadata.name,
                "type": result.spec.type,
                "cluster_ip": result.spec.cluster_ip
            }

        except Exception as e:
            logger.error(f"Error creating service: {e}")
            return {"error": str(e)}

    async def _create_ingress(self, workload: Workload, namespace: str) -> Dict[str, Any]:
        """Create Kubernetes ingress."""
        try:
            networking_v1 = client.NetworkingV1Api(self.api_client)

            ingress = client.V1Ingress(
                metadata=client.V1ObjectMeta(
                    name=f"gpu-ingress-{workload.id}",
                    namespace=namespace,
                    annotations={
                        "kubernetes.io/ingress.class": "nginx",
                        "nginx.ingress.kubernetes.io/rewrite-target": "/"
                    }
                ),
                spec=client.V1IngressSpec(
                    rules=[
                        client.V1IngressRule(
                            host=f"workload-{workload.id}.cloudarb.local",
                            http=client.V1HTTPIngressRuleValue(
                                paths=[
                                    client.V1HTTPIngressPath(
                                        path="/",
                                        path_type="Prefix",
                                        backend=client.V1IngressBackend(
                                            service=client.V1IngressServiceBackend(
                                                name=f"gpu-service-{workload.id}",
                                                port=client.V1ServiceBackendPort(
                                                    number=80
                                                )
                                            )
                                        )
                                    )
                                ]
                            )
                        )
                    ]
                )
            )

            result = networking_v1.create_namespaced_ingress(
                namespace=namespace,
                body=ingress
            )

            return {
                "name": result.metadata.name,
                "host": result.spec.rules[0].host
            }

        except Exception as e:
            logger.error(f"Error creating ingress: {e}")
            return {"error": str(e)}

    async def delete_workload(self, workload_id: str, namespace: str) -> Dict[str, Any]:
        """Delete workload from Kubernetes."""
        try:
            if not self.api_client:
                return {"success": False, "error": "Kubernetes client not initialized"}

            # Delete deployment
            apps_v1 = client.AppsV1Api(self.api_client)
            apps_v1.delete_namespaced_deployment(
                name=f"gpu-workload-{workload_id}",
                namespace=namespace
            )

            # Delete service
            v1 = client.CoreV1Api(self.api_client)
            v1.delete_namespaced_service(
                name=f"gpu-service-{workload_id}",
                namespace=namespace
            )

            # Delete ingress
            networking_v1 = client.NetworkingV1Api(self.api_client)
            networking_v1.delete_namespaced_ingress(
                name=f"gpu-ingress-{workload_id}",
                namespace=namespace
            )

            # Delete namespace
            v1.delete_namespace(namespace)

            return {"success": True}

        except Exception as e:
            logger.error(f"Error deleting workload from Kubernetes: {e}")
            return {"success": False, "error": str(e)}


class InfrastructureManager:
    """Main infrastructure management service."""

    def __init__(self):
        self.terraform_manager = TerraformManager()
        self.k8s_manager = KubernetesManager()
        self.active_deployments = {}

    async def deploy_workload(self, workload: Workload,
                            allocation: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy workload using the appropriate infrastructure method."""
        try:
            deployment_type = allocation.get("deployment_type", "terraform")

            if deployment_type == "terraform":
                result = await self.terraform_manager.create_infrastructure(workload, allocation)
            elif deployment_type == "kubernetes":
                result = await self.k8s_manager.deploy_workload(workload, allocation)
            else:
                return {"success": False, "error": f"Unsupported deployment type: {deployment_type}"}

            if result["success"]:
                # Store deployment info
                self.active_deployments[workload.id] = {
                    "allocation": allocation,
                    "deployment_type": deployment_type,
                    "result": result,
                    "deployed_at": datetime.utcnow()
                }

                # Record metrics
                metrics_collector.record_workload_deployment(workload.id, allocation.get("provider"))

            return result

        except Exception as e:
            logger.error(f"Error deploying workload: {e}")
            return {"success": False, "error": str(e)}

    async def destroy_workload(self, workload_id: str) -> Dict[str, Any]:
        """Destroy workload infrastructure."""
        try:
            if workload_id not in self.active_deployments:
                return {"success": False, "error": "Workload not found in active deployments"}

            deployment_info = self.active_deployments[workload_id]
            deployment_type = deployment_info["deployment_type"]

            if deployment_type == "terraform":
                result = await self.terraform_manager.destroy_infrastructure(
                    deployment_info["result"].get("infrastructure_id", workload_id)
                )
            elif deployment_type == "kubernetes":
                result = await self.k8s_manager.delete_workload(
                    workload_id,
                    deployment_info["result"].get("namespace", f"cloudarb-{workload_id}")
                )
            else:
                return {"success": False, "error": f"Unsupported deployment type: {deployment_type}"}

            if result["success"]:
                # Remove from active deployments
                del self.active_deployments[workload_id]

                # Record metrics
                metrics_collector.record_workload_destruction(workload_id)

            return result

        except Exception as e:
            logger.error(f"Error destroying workload: {e}")
            return {"success": False, "error": str(e)}

    async def get_deployment_status(self, workload_id: str) -> Dict[str, Any]:
        """Get deployment status for a workload."""
        try:
            if workload_id not in self.active_deployments:
                return {"status": "not_found"}

            deployment_info = self.active_deployments[workload_id]

            return {
                "status": "active",
                "deployment_type": deployment_info["deployment_type"],
                "deployed_at": deployment_info["deployed_at"].isoformat(),
                "allocation": deployment_info["allocation"],
                "result": deployment_info["result"]
            }

        except Exception as e:
            logger.error(f"Error getting deployment status: {e}")
            return {"status": "error", "error": str(e)}

    async def list_active_deployments(self) -> List[Dict[str, Any]]:
        """List all active deployments."""
        try:
            deployments = []
            for workload_id, info in self.active_deployments.items():
                deployments.append({
                    "workload_id": workload_id,
                    "deployment_type": info["deployment_type"],
                    "deployed_at": info["deployed_at"].isoformat(),
                    "provider": info["allocation"].get("provider"),
                    "instance_type": info["allocation"].get("instance_type")
                })

            return deployments

        except Exception as e:
            logger.error(f"Error listing active deployments: {e}")
            return []


# Global infrastructure manager instance
infrastructure_manager = InfrastructureManager()


async def deploy_optimized_allocation(workload: Workload,
                                    allocation: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy an optimized allocation."""
    try:
        result = await infrastructure_manager.deploy_workload(workload, allocation)

        if result["success"]:
            logger.info(f"Successfully deployed workload {workload.id}")
        else:
            logger.error(f"Failed to deploy workload {workload.id}: {result['error']}")

        return result

    except Exception as e:
        logger.error(f"Error deploying optimized allocation: {e}")
        return {"success": False, "error": str(e)}


async def destroy_workload_infrastructure(workload_id: str) -> Dict[str, Any]:
    """Destroy workload infrastructure."""
    try:
        result = await infrastructure_manager.destroy_workload(workload_id)

        if result["success"]:
            logger.info(f"Successfully destroyed workload {workload_id}")
        else:
            logger.error(f"Failed to destroy workload {workload_id}: {result['error']}")

        return result

    except Exception as e:
        logger.error(f"Error destroying workload infrastructure: {e}")
        return {"success": False, "error": str(e)}