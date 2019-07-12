#!/usr/bin/env python3

# CDK v1.0.0
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
                export_name="{}-ecs-cluster-sec-grp".format(self.stack_name)
        )
        
        # Adding an output for other resources to access
        self.vpc_id = core.CfnOutput(
                self, "VPCId",
                value=self.vpc.vpc_id,
                export_name="{}-vpc-id".format(self.stack_name)
        )
        
        # Adding service discovery namespace to cluster
        self.ecs_cluster.add_default_cloud_map_namespace(
            name="service",
        )

        # Adding service discovery outputs for other resources to access
        self.sd_name = core.CfnOutput(self, "ServiceDiscoveryName",value=self.ecs_cluster.default_cloud_map_namespace.namespace_name, export_name=self.stack_name + "-service-discovery-name")
        self.sd_id = core.CfnOutput(self, "ServiceDiscoveryId",value=self.ecs_cluster.default_cloud_map_namespace.namespace_id, export_name=self.stack_name + "-service-discovery-id")
        self.sd_arn = core.CfnOutput(self, "ServiceDiscoveryArn",value=self.ecs_cluster.default_cloud_map_namespace.namespace_arn, export_name=self.stack_name + "-service-discovery-arn")
        
        # Adding an output for other resources to access
        self.ecs_cluster_output = core.CfnOutput(
                self, "ECSClusterOutput",
                value=self.ecs_cluster.cluster_name,
                export_name="{}-ecs-cluster-name".format(self.stack_name)
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
                export_name="{}-backend-services-security-group-id".format(self.stack_name)
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


if __name__ == '__main__':
    from os import environ

    _stack_name = 'fargate-demo'
    # https://github.com/awslabs/aws-cdk/issues/3082
    _env = {'account': environ['CDK_DEFAULT_ACCOUNT'],'region': environ['CDK_DEFAULT_REGION']}
    
    app = core.App()
    BaseVPCStack(app, _stack_name + "-base")
    app.synth()
