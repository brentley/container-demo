## Bring up a cloud9 IDE and run these prerequisite commands:
```
# Choose your region, and store it in this environment variable

export AWS_DEFAULT_REGION=<aws-region-here> # Example region: us-west-2
echo "export AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION >> ~/.bashrc"
```

AWS CDK pre-requisites:

- [Node.js](https://nodejs.org/en/download) >= 8.11.x

- Python >= 3.6

or

- Docker

Not using Docker:
```
npm install -g aws-cdk
cdk --version
virtual env .env
source .env/bin/activate
pip install --upgrade -r requirements.txt
```
Using Docker:
```
CDK_VERSION=v0.35.0
function _cdk { docker run -v $(pwd):/cdk -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN -e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -it adam9098/aws-cdk:${CDK_VERSION} $@; }
```

This installs the required libraries to run cdk. Choosing the Docker path takes a lot of the pain of having to install the libraries locally.

## Clone this demo repository:
```
cd ~/environment
git clone https://github.com/brentley/fargate-demo.git
```

## Clone our application microservice repositories:
```
cd ~/environment
git clone https://github.com/brentley/ecsdemo-frontend.git
git clone https://github.com/brentley/ecsdemo-nodejs.git
git clone https://github.com/brentley/ecsdemo-crystal.git
```

## Build a base stack (VPC, ECS Cluster, Service Discovery Namespace, Base Security Group)
![infrastructure](images/private-subnet-public-lb.png)
```
cd ~/environment/fargate-demo
```
First, let's confirm that our code can properly synthesize and create the outputs.
```
_cdk synth 
```

*Note: If you receive the following error:
```
--app is required either in command-line, in cdk.json or in ~/.cdk.json
```
Create a file `cdk.json` with the following contents:
```
{
    "app": "python3 app.py"
}
```

You should now see CloudFormation templates in the `cdk.out` directory, along with some other files related to cdk deployment.

Now, let's build out the baseline environment
```
_cdk deploy fargate-demo-base
```

At a high level, we are building what you see in the diagram. We will have 3 
availability zones, each with a public and private subnet. The public subnets
will hold service endpoints, and the private subnets will be where our workloads run.
Where the image shows an instance, we will have containers on AWS Fargate.

## Deploy our frontend application:

Let's deploy the frontend application. This will be comprised of an Application Load Balancer, and a container running on ECS Fargate. First, we will run a diff to see what is set to be deployed. If this is a first time build, you should see all of the resources that are slated for creation. Once you review, deploy it!
```
cd ~/environment
_cdk diff fargate-demo-frontend
_cdk deploy fargate-demo-frontend
```

We have defined our frontend application as its own stack in the cdk codebase. This provides a layer of isolation specific to the frontend application. This is an ideal way to split up your infrastructure deployments to ensure you limit blast radius to small functional groups.

## View running container:
```
ecs-cli compose --project-name ecsdemo-frontend service ps \
    --cluster-config fargate-demo
```
We should have one task registered.

## Check reachability (open url in your browser):
```
alb_url=$(aws cloudformation describe-stacks --stack-name fargate-demo-alb --query 'Stacks[0].Outputs[?OutputKey==`ExternalUrl`].OutputValue' --output text)
echo "Open $alb_url in your browser"
```
This command looks up the URL for our ingress ALB, and outputs it. You should 
be able to click to open, or copy-paste into your browser.

## View logs:
```
#substitute your task id from the ps command 
ecs-cli logs --task-id a06a6642-12c5-4006-b1d1-033994580605 \
    --follow --cluster-config fargate-demo
```
To view logs, find the task id from the earlier `ps` command, and use it in this
command. You can follow a task's logs also.

## Scale the tasks:
```
ecs-cli compose --project-name ecsdemo-frontend service scale 3 \
    --cluster-config fargate-demo
ecs-cli compose --project-name ecsdemo-frontend service ps \
    --cluster-config fargate-demo
```
We can see that our containers have now been evenly distributed across all 3 of our
availability zones.

## Bring up NodeJS backend api:
```
cd ~/environment/ecsdemo-nodejs
envsubst <ecs-params.yml.template >ecs-params.yml
ecs-cli compose --project-name ecsdemo-nodejs service up \
    --create-log-groups \
    --private-dns-namespace service \
    --enable-service-discovery \
    --cluster-config fargate-demo \
    --vpc $vpc

```
Just like earlier, we are now bringing up one of our backend API services.
This service is not registered with any ALB, and instead is only reachable by 
private IP in the VPC, so we will use service discovery to talk to it.

## Scale the tasks:
```
ecs-cli compose --project-name ecsdemo-nodejs service scale 3 \
    --cluster-config fargate-demo
    
```
We can see that our containers have now been evenly distributed across all 3 of our
availability zones.

## Bring up Crystal backend api:
```
cd ~/environment/ecsdemo-crystal
envsubst <ecs-params.yml.template >ecs-params.yml
ecs-cli compose --project-name ecsdemo-crystal service up \
    --create-log-groups \
    --private-dns-namespace service \
    --enable-service-discovery \
    --cluster-config fargate-demo \
    --vpc $vpc

```
Just like earlier, we are now bringing up one of our backend API services.
This service is not registered with any ALB, and instead is only reachable by 
private IP in the VPC, so we will use service discovery to talk to it.

## Scale the tasks:
```
ecs-cli compose --project-name ecsdemo-crystal service scale 3 \
    --cluster-config fargate-demo
    
```
We can see that our containers have now been evenly distributed across all 3 of our
availability zones.

## Conclusion:
You should now have 3 services, each running 3 tasks, spread across 3 availability zones.
Additionally you should have zero instances to manage. :)

## Cleanup:
```
cd ~/environment/ecsdemo-frontend
ecs-cli compose --project-name ecsdemo-frontend service down --cluster-config fargate-demo
cd ~/environment/ecsdemo-nodejs
ecs-cli compose --project-name ecsdemo-nodejs service down --cluster-config fargate-demo
cd ~/environment/ecsdemo-crystal
ecs-cli compose --project-name ecsdemo-crystal service down --cluster-config fargate-demo

ecs-cli down --force --cluster-config fargate-demo
aws cloudformation delete-stack --stack-name fargate-demo-alb
aws cloudformation wait stack-delete-complete --stack-name fargate-demo-alb
aws cloudformation delete-stack --stack-name fargate-demo
aws cloudformation delete-stack --stack-name amazon-ecs-cli-setup-private-dns-namespace-$clustername-ecsdemo-frontend
```


