## Status: Beta
## Bring up a cloud9 IDE and run these prerequisite commands:
```bash
# Choose your region, and store it in this environment variable

export AWS_DEFAULT_REGION=<aws-region-here> # Example region: us-west-2
echo "export AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION >> ~/.bashrc"

# Install ecs-cli
sudo curl -so /usr/local/bin/ecs-cli https://s3.amazonaws.com/amazon-ecs-cli/ecs-cli-linux-amd64-latest
sudo chmod +x /usr/local/bin/ecs-cli
```

AWS CDK pre-requisites:

- [Node.js](https://nodejs.org/en/download) >= 8.11.x

- Python >= 3.6

or

- Docker

Not using Docker:
```bash
CDK_VERSION=v0.36.0
npm install -g aws-cdk@${CDK_VERSION}
cdk --version
virtual env .env
source .env/bin/activate
pip install --upgrade -r requirements.txt
```
Using Docker:
```bash
CDK_VERSION=v0.36.0
function _cdk { docker run -v $(pwd):/cdk -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN -e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -it adam9098/aws-cdk:${CDK_VERSION} $@; }
```

This installs the required libraries to run cdk. Choosing the Docker path takes a lot of the pain of having to install the libraries locally.

## Clone this demo repository:
```bash
cd ~/environment
git clone https://github.com/brentley/fargate-demo.git
```

## Clone our application microservice repositories. NOTE: This is not required, but simply an option to give you visibility into the services being deployed.
```bash
cd ~/environment
git clone https://github.com/brentley/ecsdemo-frontend.git
git clone https://github.com/brentley/ecsdemo-nodejs.git
git clone https://github.com/brentley/ecsdemo-crystal.git
```

## Build a base stack (VPC, ECS Cluster, Service Discovery Namespace, Base Security Group)
![infrastructure](images/private-subnet-public-lb.png)
```bash
cd ~/environment/fargate-demo
```
First, let's confirm that our code can properly synthesize and create the outputs.
```
_cdk synth 
```

You should now see CloudFormation templates in the `cdk.out` directory, along with some other files related to cdk deployment.

Now, let's build out the baseline environment
```bash
_cdk deploy fargate-demo-base
```

At the end of the deploy, cdk will show you a list of the outputs and their values. Find the output that is the ECS Cluster name. Export this as an environment variable, we will need this for communicating with ecs via the command line.
Using the ecs-cli, we will setup the cli to communicate with the cluster.
```
Outputs:

fargate-demo-base.ExportsOutputRefECSCluster7D463CD47A8DFE2F = fargate-demo-base-ECSCluster7D463CD4-IH4IZATNP701
```

```bash
export ECS_CLUSTER_NAME="fargate-demo-base-ECSCluster7D463CD4-IH4IZATNP701"

ecs-cli configure -c ${ECS_CLUSTER_NAME} -r ${AWS_DEFAULT_REGION}

```

At a high level, we are building what you see in the diagram. We will have 3 
availability zones, each with a public and private subnet. The public subnets
will hold service endpoints, and the private subnets will be where our workloads run.
Where the image shows an instance, we will have containers on AWS Fargate.

What's nice about using the cdk, is that you can rely on the service to make opinionated decisions based on well architected patterns. For example:

```python
self.vpc = aws_ec2.Vpc(
    self, "BaseVPC",
    cidr='10.0.0.0/24',
    enable_dns_support=True,
    enable_dns_hostnames=True,
)
```

In the above code snippet, we simply defined our cidr notation for the vpc, and cdk will provision subnets to span across three availability zones, as well as splitting up the address blocks per subnet evenly. Not only that, but it will create public and private subnets along with Internet/NAT Gateways. Now of course, if you want to define this on your own, cdk allows for that as well.

## Deploy our frontend application:

Let's deploy the frontend application. This will be comprised of an Application Load Balancer, and a container running on ECS Fargate. First, we will run a diff to see what is set to be deployed. If this is a first time build, you should see all of the resources that are slated for creation. Once you review, deploy it!
```bash
cd ~/environment
_cdk diff fargate-demo-frontend
_cdk deploy fargate-demo-frontend
```

The deployment will take place and provide outputs as it progresses. When complete, copy the outputs to a file for further use.

```
Outputs:
fargate-demo-frontend.FrontendFargateLBServiceLoadBalancerDNSAFFB8F0B = farga-Front-17NF2P95ABONI-525673116.us-west-2.elb.amazonaws.com
```

The output is a url for the load balancer that was just created. Open the url in your browser and you should see it running your frontend service!

Once again we are using an opinionated library within the cdk that will do the heavy lifting of creating the resources for the load balanced ecs fargate service. Let's take a look at the code:

```python
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
    load_balancer_type=aws_ecs_patterns.LoadBalancerType('Application'),
    public_load_balancer=True,
    environment={
        "CRYSTAL_URL": "http://ecsdemo-crystal.service:3000/crystal",
        "NODEJS_URL": "http://ecsdemo-nodejs.service:3000"
    },
)
```

We have defined our frontend application as its own stack in the cdk codebase. This provides a layer of isolation specific to the frontend application. This is an ideal way to split up your infrastructure deployments to ensure you limit blast radius to small functional groups.

## View running containers:
```
ecs-cli ps
```
Here is an example response:
```
Name                                      State    Ports                      TaskDefinition                                                Health
391bb0ca-da0f-48b1-b982-acb75ec7d975/web  RUNNING  10.0.0.107:3000->3000/tcp  fargatedemofrontendFrontendFargateLBServiceTaskDefC747F090:1  UNKNOWN
```

We should have one task registered, and you should see three instances of that task running.

## View logs:

Let's see the log output for one of the tasks. Run the following command to tail the logs live:

```
#substitute your task id from the ps command 
ecs-cli logs -t --since 5 --task-id 391bb0ca-da0f-48b1-b982-acb75ec7d97
```
To view logs, find the task id from the earlier `ps` command, and use it in this
command. You can follow a task's logs also.

## Scale the tasks:
Open up in an editor of your choice `app.py`, and we will modify the frontend stack and up the desired count from 1 to 3. Simply comment the variable
`desired_service_count=1`, and uncomment `desired_service_count=3`.

```python
        # Frontend service stack
        self.frontend_service = FrontendECSService(self, self.stack_name + "-frontend",
                                           self.base_module.ecs_cluster, self.base_module.vpc,
                                           self.base_module.services_3000_sec_group,
                                           #desired_service_count=1)
                                           desired_service_count=3)
```

Let's run a diff to see what changes will be made, and then deploy!

```
_cdk diff fargate-demo-frontend
_cdk deploy fargate-demo-frontend
```

Run the following again to see how many containers are running in the cluster:

```
ecs-cli ps
```

We can see that our containers have now been evenly distributed across all 3 of our
availability zones.

## Bring up NodeJS backend api:
```bash
cd ~/environment
_cdk diff fargate-demo-node-backend
_cdk deploy fargate-demo-node-backend
```

Just like earlier, we are now bringing up one of our backend API services.
This service is not registered with any ALB, and instead is only reachable by 
private IP in the VPC, so we will use service discovery to talk to it. 
The containers will automatically register with CloudMap on launch.

## Scale the tasks:
Open up in an editor of your choice `app.py`, and we will modify the frontend stack and up the desired count from 1 to 3. Simply comment the variable
`desired_service_count=1`, and uncomment `desired_service_count=3`.

```python
# Backend Node.js service
self.backend_node_service = BackendNodeECSService(self, self.stack_name + "-node-backend",
                                                    self.base_module.ecs_cluster,self.base_module.vpc,
                                                    self.base_module.services_3000_sec_group,
                                                    #desired_service_count=1)
                                                    desired_service_count=3)
```

Let's run a diff to see what changes will be made, and then deploy!

```
_cdk diff fargate-demo-node-backend
_cdk deploy fargate-demo-node-backend
```

```
ecs-cli ps
```

## Bring up Crystal backend api:
```bash
cd ~/environment
_cdk diff fargate-demo-crystal-backend
_cdk deploy fargate-demo-crystal-backend
```

Just like earlier, we are now bringing up one of our backend API services.
This service is not registered with any ALB, and instead is only reachable by 
private IP in the VPC, so we will use service discovery to talk to it. 
The containers will automatically register with CloudMap on launch.
```

## Scale the tasks:
Open up in an editor of your choice `app.py`, and we will modify the frontend stack and up the desired count from 1 to 3. Simply comment the variable
`desired_service_count=1`, and uncomment `desired_service_count=3`.

```python
# Backend Crystal service
self.backend_crystal_service = BackendCrystalECSService(self, self.stack_name + "-crystal-backend",
                                                    self.base_module.ecs_cluster,self.base_module.vpc,
                                                    self.base_module.services_3000_sec_group,
                                                    #desired_service_count=1)
                                                    desired_service_count=3)
```

Let's run a diff to see what changes will be made, and then deploy!

```
_cdk diff fargate-demo-crystal-backend
_cdk deploy fargate-demo-crystal-backend
```

```
ecs-cli ps
```

We can see that our containers have now been evenly distributed across all 3 of our
availability zones.

## Conclusion:
You should now have 3 services, each running 3 tasks, spread across 3 availability zones.
Additionally you should have zero instances to manage. :)

## Cleanup:
```
_cdk destroy
```


