#!/usr/bin/env python3

# CDK v0.36.0
from aws_cdk import (
    aws_ec2,
    aws_ecs,
    aws_ecs_patterns,
    aws_elasticloadbalancingv2,
    aws_logs,
    aws_servicediscovery,
    core,
)


class BaseVPCStack(core.Stack):

    def __init__(self, scope: core.Stack, id=str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # This resource alone will create a private/public subnet in each AZ as well as nat/internet gateway(s)
        self.vpc = aws_ec2.Vpc(
            self, "BaseVPC",
            cidr='10.0.0.0/24',
            enable_dns_support=True,
            enable_dns_hostnames=True,
        )

        # Creating ECS Cluster in the VPC created above
        self.ecs_cluster = aws_ecs.Cluster(
            self, "ECSCluster",
            vpc=self.vpc
        )
        
        self.ecs_cluster.vpc.vpc_default_security_group
        # Adding an output for other resources to access when importing an ecs cluster
        self.ecs_cluster_output = core.CfnOutput(
                self, "ECSClusterSecGrp",
                value=self.ecs_cluster.vpc.vpc_default_security_group,
                export_name="ECS-CLUSTER-SEC-GRP"
        )
        
        # Adding an output for other resources to access
        self.vpc_id = core.CfnOutput(
                self, "VPCId",
                value=self.vpc.vpc_id,
                export_name=self.stack_name + "-vpc-id"
        )
        
        # Adding service discovery namespace to cluster
        self.ecs_cluster.add_default_cloud_map_namespace(
            name="service",
        )
        
        # Adding an output for other resources to access
        self.ecs_cluster_output = core.CfnOutput(
                self, "ECSClusterOutput",
                value=self.ecs_cluster.cluster_name,
                #value=self.ecs_cluster.cluster_name,
                export_name="ECS-CLUSTER-NAME"
        )

        # Frontend security group frontend service to backend services
        self.services_3000_sec_group = aws_ec2.SecurityGroup(
            self, "FrontendToBackendSecurityGroup",
            allow_all_outbound=True,
            description="Security group for frontend service to talk to backend services",
            vpc=self.vpc
        )
        
        # Adding an output for other resources to access
        self.security_group_export = core.CfnOutput(
                self, "SGOutput",
                value=self.services_3000_sec_group.security_group_id,
                export_name="BACKEND-SERVICES-SECURITY-GROUP-ID"
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


class FargateDemo(core.App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.stack_name = "fargate-demo"

        # Base stack (networking, security groups, etc)
        self.base_module = BaseVPCStack(self, self.stack_name + "-base")


if __name__ == '__main__':
    app = FargateDemo()
    app.synth()
