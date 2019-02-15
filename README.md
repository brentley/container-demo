
```
sudo yum -y install jq gettext
sudo curl -so /usr/local/bin/ecs-cli https://s3.amazonaws.com/amazon-ecs-cli/ecs-cli-linux-amd64-latest
sudo chmod +x /usr/local/bin/ecs-cli
```

```
aws cloudformation deploy --stack-name fargate-demo --template-file cluster-fargate-private-vpc.yml --capabilities CAPABILITY_IAM
aws cloudformation deploy --stack-name fargate-demo-alb --template-file alb-external.yml

export clustername=$(aws cloudformation describe-stacks --stack-name fargate-demo --query 'Stacks[0].Outputs[?OutputKey==`ClusterName`].OutputValue' --output text)
export target_group_arn=$(aws cloudformation describe-stack-resources --stack-name fargate-demo-alb | jq -r '.[][] | select(.ResourceType=="AWS::ElasticLoadBalancingV2::TargetGroup").PhysicalResourceId')

#ecs-cli configure --region ap-southeast-1 --cluster $clustername --default-launch-type FARGATE --config-name fargate-demo
ecs-cli configure --region $AWS_DEFAULT_REGION --cluster $clustername --default-launch-type FARGATE --config-name fargate-demo

export vpc=$(aws cloudformation describe-stacks --stack-name fargate-demo --query 'Stacks[0].Outputs[?OutputKey==`VpcId`].OutputValue' --output text)
export subnet_1=$(aws cloudformation describe-stacks --stack-name fargate-demo --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnetOne`].OutputValue' --output text)
export subnet_2=$(aws cloudformation describe-stacks --stack-name fargate-demo --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnetTwo`].OutputValue' --output text)
export subnet_3=$(aws cloudformation describe-stacks --stack-name fargate-demo --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnetThree`].OutputValue' --output text)
export security_group=$(aws cloudformation describe-stacks --stack-name fargate-demo --query 'Stacks[0].Outputs[?OutputKey==`ContainerSecurityGroup`].OutputValue' --output text)

aws ec2 authorize-security-group-ingress --group-id "$security_group" --protocol tcp --port 3000 --cidr 0.0.0.0/0

cd ~/environment/ecsdemo-frontend
envsubst < ecs-params.yml.template >ecs-params.yml

ecs-cli compose --project-name ecsdemo-frontend service up \
    --create-log-groups \
    --target-group-arn $target_group_arn \
    --private-dns-namespace service \
    --enable-service-discovery \
    --container-name ecsdemo-frontend \
    --container-port 3000 \
    --cluster-config fargate-demo \
    --vpc $vpc
    
```

view running containers:
```
ecs-cli compose --project-name ecsdemo-frontend service ps \
    --cluster-config fargate-demo
```

check reachability:
```
alb_url=$(aws cloudformation describe-stacks --stack-name fargate-demo-alb --query 'Stacks[0].Outputs[?OutputKey==`ExternalUrl`].OutputValue' --output text)
echo "Open $alb_url in your browser"
```

view logs:
```
#substitute your task id from the previous command 
ecs-cli logs --task-id a06a6642-12c5-4006-b1d1-033994580605 \
    --follow --cluster-config fargate-demo
```

scale the tasks:
```
ecs-cli compose --project-name ecsdemo-frontend service scale 3 \
    --cluster-config fargate-demo
ecs-cli compose --project-name ecsdemo-frontend service ps \
    --cluster-config fargate-demo
```

bring up nodejs backend api:
```
cd ~/environment/ecsdemo-nodejs
envsubst <ecs-params.yml.template >ecs-params.yml
ecs-cli compose --project-name ecsdemo-nodejs service up \
    --create-log-groups \
    --private-dns-namespace service \
    --enable-service-discovery \
    --container-name ecsdemo-nodejs \
    --container-port 3000 \
    --cluster-config fargate-demo \
    --vpc $vpc

```

bring up crystal backend api:
```
cd ~/environment/ecsdemo-crystal
envsubst <ecs-params.yml.template >ecs-params.yml
ecs-cli compose --project-name ecsdemo-crystal service up \
    --create-log-groups \
    --private-dns-namespace service \
    --enable-service-discovery \
    --container-name ecsdemo-crystal \
    --container-port 3000 \
    --cluster-config fargate-demo \
    --vpc $vpc

```

cleanup:
```
ecs-cli compose --project-name ecsdemo-frontend service down --cluster-config fargate-demo
ecs-cli compose --project-name ecsdemo-nodejs service down --cluster-config fargate-demo
ecs-cli compose --project-name ecsdemo-crystal service down --cluster-config fargate-demo
ecs-cli compose --project-name ecsdemo-frontend service rm
ecs-cli compose --project-name ecsdemo-nodejs service rm
ecs-cli compose --project-name ecsdemo-crystal service rm --delete-namespace

ecs-cli down --force --cluster-config fargate-demo
aws cloudformation delete-stack --stack-name fargate-demo-alb
aws cloudformation wait stack-delete-complete --stack-name fargate-demo-alb
aws cloudformation delete-stack --stack-name fargate-demo
aws cloudformation wait stack-delete-complete --stack-name fargate-demo
```


