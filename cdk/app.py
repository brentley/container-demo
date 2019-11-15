#!/usr/bin/env python3

from aws_cdk import (
    aws_ec2,
    aws_ecs,
    core
)

from os import getenv


class Platform(core.Stack):

    def __init__(self, scope: core.Stack, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Creates all components to have a functional network within the VPC
        self.vpc = aws_ec2.Vpc(
            self, "Vpc",
            cidr='10.0.0.0/16',
        )

        # Creates ECS cluster in the above VPC with a Cloud Map Namespace called "service"
        self.cluster = aws_ecs.Cluster(
            self, "ECSCluster",
            vpc=self.vpc,
            default_cloud_map_namespace=aws_ecs.CloudMapNamespaceOptions(
                name="service"
            )
        )

        if getenv('EC2_ENABLED'):

            # Adds compute capacity to a cluster by creating an AutoScalingGroup with the specified options.
            self.cluster.add_capacity(
                "ECSClusterCapacity",
                instance_type=aws_ec2.InstanceType("t3.large"),
                desired_capacity=3
            )


app = core.App()

_env = core.Environment(account=getenv('CDK_DEFAULT_ACCOUNT'), region=getenv('AWS_DEFAULT_REGION'))

Platform(app, "ecsworkshop", env=_env)

app.synth()

