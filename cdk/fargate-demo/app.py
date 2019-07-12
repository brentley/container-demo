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

        # Adding service discovery namespace to cluster
        self.ecs_cluster.add_default_cloud_map_namespace(
            name="service",
        )

        # Frontend security group frontend service to backend services
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


class FrontendECSService(core.Stack):

    def __init__(self, scope: core.Stack, id: str, ecs_cluster, vpc, services_3000_sec_group, desired_service_count, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.ecs_cluster = ecs_cluster
        self.vpc = vpc
        self.services_3000_sec_group = services_3000_sec_group
        self.desired_service_count = desired_service_count

        # This will create an ALB with listener/target group, ecs task def, ecs fargate service, logging in cloudwatch
        # and security group from ALB to containers. This essentially condenses 95 lines of code into 15.
        self.fargate_load_balanced_service = aws_ecs_patterns.LoadBalancedFargateService(
            self, "FrontendFargateLBService",
            cluster=self.ecs_cluster,
            image=aws_ecs.ContainerImage.from_registry("brentley/ecsdemo-frontend"),
            container_port=3000,
            cpu=256,
            memory_limit_mi_b=512,
            enable_logging=True,
            desired_count=self.desired_service_count,
            load_balancer_type=aws_ecs_patterns.LoadBalancerType('APPLICATION'),
            public_load_balancer=True,
            environment={
                "CRYSTAL_URL": "http://ecsdemo-crystal.service:3000/crystal",
                "NODEJS_URL": "http://ecsdemo-nodejs.service:3000"
            },
        )


        # There has to be a better way, but for now this is what we got.
        # Allow inbound 3000 from Frontend Service to Backend
        self.sec_grp_ingress_backend_to_frontend_3000 = aws_ec2.CfnSecurityGroupIngress(
            self, "InboundBackendSecGrp3000",
            ip_protocol='TCP',
            source_security_group_id=self.fargate_load_balanced_service.service.connections.security_groups[0].security_group_id,
            from_port=3000,
            to_port=3000,
            group_id=self.services_3000_sec_group.security_group_id
        )

        # There has to be a better way, but for now this is what we got.
        # Allow inbound 3000 Backend to Frontend Service
        self.sec_grp_ingress_frontend_to_backend_3000 = aws_ec2.CfnSecurityGroupIngress(
            self, "InboundFrontendtoBackendSecGrp3000",
            ip_protocol='TCP',
            source_security_group_id=self.services_3000_sec_group.security_group_id,
            from_port=3000,
            to_port=3000,
            group_id=self.fargate_load_balanced_service.service.connections.security_groups[0].security_group_id,
        )        


class BackendCrystalECSService(core.Stack):

    def __init__(self, scope: core.Stack, id: str, ecs_cluster, vpc, services_3000_sec_group, desired_service_count, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.ecs_cluster = ecs_cluster
        self.vpc = vpc
        self.service_discovery = self.ecs_cluster.default_cloud_map_namespace
        self.services_3000_sec_group = services_3000_sec_group
        self.desired_service_count = desired_service_count


        self.task_definition = aws_ecs.FargateTaskDefinition(
            self, "BackendCrystalServiceTaskDef",
            cpu=256,
            memory_limit_mi_b=512,
        )

        self.task_definition.add_container(
            "BackendCrystalServiceContainer",
            image=aws_ecs.ContainerImage.from_registry("adam9098/ecsdemo-crystal"),
            #image=aws_ecs.ContainerImage.from_registry("brentley/ecsdemo-crystal"),
            logging=aws_ecs.AwsLogDriver(stream_prefix="ecsdemo-crystal", log_retention=aws_logs.RetentionDays.THREE_DAYS),
        )

        self.fargate_service = aws_ecs.FargateService(
            self, "BackendCrystalFargateService",
            service_name="ecsdemo-crystal",
            task_definition=self.task_definition,
            cluster=self.ecs_cluster,
            max_healthy_percent=100,
            min_healthy_percent=0,
            vpc_subnets=self.vpc.private_subnets,
            desired_count=self.desired_service_count,
            cloud_map_options={
                "name": "ecsdemo-crystal"
            },
            security_group=self.services_3000_sec_group,
        )


class BackendNodeECSService(core.Stack):

    def __init__(self, scope: core.Stack, id: str, ecs_cluster, vpc, services_3000_sec_group, desired_service_count, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.ecs_cluster = ecs_cluster
        self.vpc = vpc
        self.service_discovery = self.ecs_cluster.default_cloud_map_namespace
        self.services_3000_sec_group = services_3000_sec_group
        self.desired_service_count = desired_service_count

        self.task_definition = aws_ecs.FargateTaskDefinition(
            self, "BackendNodeServiceTaskDef",
            cpu=256,
            memory_limit_mi_b=512,
        )

        self.task_definition.add_container(
            "BackendNodeServiceContainer",
            image=aws_ecs.ContainerImage.from_registry("brentley/ecsdemo-nodejs"),
            logging=aws_ecs.AwsLogDriver(stream_prefix="ecsdemo-nodejs", log_retention=aws_logs.RetentionDays.THREE_DAYS),
        )

        self.fargate_service = aws_ecs.FargateService(
            self, "BackendNodeFargateService",
            service_name="ecsdemo-nodejs",
            task_definition=self.task_definition,
            cluster=self.ecs_cluster,
            max_healthy_percent=100,
            min_healthy_percent=0,
            vpc_subnets=self.vpc.private_subnets,
            desired_count=self.desired_service_count,
            cloud_map_options={
                "name": "ecsdemo-nodejs"
            },
            security_group=self.services_3000_sec_group,
        )


class FargateDemo(core.App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.stack_name = "fargate-demo"

        # Base stack (networking, security groups, etc)
        self.base_module = BaseVPCStack(self, self.stack_name + "-base")

        # Frontend service stack
        self.frontend_service = FrontendECSService(self, self.stack_name + "-frontend",
                                           self.base_module.ecs_cluster, self.base_module.vpc,
                                           self.base_module.services_3000_sec_group,
                                           desired_service_count=1)
                                           #desired_service_count=3)

        # Backend Crystal service
        self.backend_crystal_service = BackendCrystalECSService(self, self.stack_name + "-crystal-backend",
                                                            self.base_module.ecs_cluster,self.base_module.vpc,
                                                            self.base_module.services_3000_sec_group,
                                                            desired_service_count=1)
                                                            #desired_service_count=3)

        # Backend Node.js service
        self.backend_node_service = BackendNodeECSService(self, self.stack_name + "-node-backend",
                                                            self.base_module.ecs_cluster,self.base_module.vpc,
                                                            self.base_module.services_3000_sec_group,
                                                            desired_service_count=1)
                                                            #desired_service_count=3)


if __name__ == '__main__':
    app = FargateDemo()
    app.synth()
