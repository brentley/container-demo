#!/usr/bin/env python3

# cdk: 1.41.0
from aws_cdk import (
    aws_ec2,
    aws_ecs,
    core,
)

from os import getenv


class BaseVPCStack(core.Stack):

    def __init__(self, scope: core.Stack, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # This resource alone will create a private/public subnet in each AZ as well as nat/internet gateway(s)
        self.vpc = aws_ec2.Vpc(
            self, "BaseVPC",
            cidr='10.0.0.0/24',
            
        )
        
        # Creating ECS Cluster in the VPC created above
        self.ecs_cluster = aws_ecs.Cluster(
            self, "ECSCluster",
            vpc=self.vpc,
            cluster_name="container-demo"
        )

        # Adding service discovery namespace to cluster
        self.ecs_cluster.add_default_cloud_map_namespace(
            name="service",
        )
        
        ###### CAPACITY PROVIDERS SECTION #####
        # Adding EC2 capacity to the ECS Cluster
        #self.asg = self.ecs_cluster.add_capacity(
        #    "ECSEC2Capacity",
        #    instance_type=aws_ec2.InstanceType(instance_type_identifier='t3.small'),
        #    min_capacity=0,
        #    max_capacity=10
        #)
        
        #core.CfnOutput(self, "EC2AutoScalingGroupName", value=self.asg.auto_scaling_group_name, export_name="EC2ASGName")
        ##### END CAPACITY PROVIDER SECTION #####
        
        # Namespace details as CFN output
        self.namespace_outputs = {
            'ARN': self.ecs_cluster.default_cloud_map_namespace.private_dns_namespace_arn,
            'NAME': self.ecs_cluster.default_cloud_map_namespace.private_dns_namespace_name,
            'ID': self.ecs_cluster.default_cloud_map_namespace.private_dns_namespace_id,
        }
        
        # Cluster Attributes
        self.cluster_outputs = {
            'NAME': self.ecs_cluster.cluster_name,
            'SECGRPS': str(self.ecs_cluster.connections.security_groups)
        }
        
        # When enabling EC2, we need the security groups "registered" to the cluster for imports in other service stacks
        if self.ecs_cluster.connections.security_groups:
            self.cluster_outputs['SECGRPS'] = str([x.security_group_id for x in self.ecs_cluster.connections.security_groups][0])
        
        # Frontend service to backend services on 3000
        self.services_3000_sec_group = aws_ec2.SecurityGroup(
            self, "FrontendToBackendSecurityGroup",
            allow_all_outbound=True,
            description="Security group for frontend service to talk to backend services",
            vpc=self.vpc
        )
        
        # Allow inbound 3000 from ALB to Frontend Service
        self.sec_grp_ingress_self_3000 = aws_ec2.CfnSecurityGroupIngress(
            self, "InboundSecGrp3000",
            ip_protocol='TCP',
            source_security_group_id=self.services_3000_sec_group.security_group_id,
            from_port=3000,
            to_port=3000,
            group_id=self.services_3000_sec_group.security_group_id
        )
        
        # All Outputs required for other stacks to build
        core.CfnOutput(self, "NSArn", value=self.namespace_outputs['ARN'], export_name="NSARN")
        core.CfnOutput(self, "NSName", value=self.namespace_outputs['NAME'], export_name="NSNAME")
        core.CfnOutput(self, "NSId", value=self.namespace_outputs['ID'], export_name="NSID")
        core.CfnOutput(self, "FE2BESecGrp", value=self.services_3000_sec_group.security_group_id, export_name="SecGrpId")
        core.CfnOutput(self, "ECSClusterName", value=self.cluster_outputs['NAME'], export_name="ECSClusterName")
        core.CfnOutput(self, "ECSClusterSecGrp", value=self.cluster_outputs['SECGRPS'], export_name="ECSSecGrpList")
        core.CfnOutput(self, "ServicesSecGrp", value=self.services_3000_sec_group.security_group_id, export_name="ServicesSecGrp")


_env = core.Environment(account=getenv('AWS_ACCOUNT_ID'), region=getenv('AWS_DEFAULT_REGION'))
stack_name = "ecsworkshop-base"
app = core.App()
BaseVPCStack(app, stack_name, env=_env)
app.synth()
