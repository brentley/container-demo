
```
sudo yum -y install jq gettext
sudo curl -so /usr/local/bin/ecs-cli https://s3.amazonaws.com/amazon-ecs-cli/ecs-cli-linux-amd64-latest
sudo chmod +x /usr/local/bin/ecs-cli
```

```
aws cloudformation deploy --stack-name fargate-demo --template-file cluster-fargate-private-vpc.yml --capabilities CAPABILITY_IAM
aws cloudformation deploy --stack-name fargate-demo-alb --template-file alb-external.yml

ecs-cli configure --region ap-southeast-1 --cluster fargate-demo --default-launch-type FARGATE --config-name fargate-demo
ecs-cli up --capability-iam
```

```
vpc=$(aws cloudformation describe-stack-resources --stack-name fargate-demo | jq -r '.[][] | select(.ResourceType=="AWS::EC2::VPC").PhysicalResourceId')
subnets=($(aws cloudformation describe-stack-resources --stack-name fargate-demo | jq -r '.[][] | select(.ResourceType=="AWS::EC2::Subnet").PhysicalResourceId'))
security_group_id=$(aws ec2 create-security-group --group-name "fargate-demo" --description "Allow Fargate Demo Web Traffic" --vpc-id "$vpc" | jq -r '.GroupId')

export security_group=$security_group_id
export subnet_1=$(echo ${subnets[0]})
export subnet_2=$(echo ${subnets[1]})
export subnet_3=$(echo ${subnets[2]})
export vpc

aws ec2 authorize-security-group-ingress --group-id "$security_group_id" --protocol tcp --port 80 --cidr 0.0.0.0/0

envsubst < ecs-params.yml.template >ecs-params.yml

```

```
ecs-cli compose --project-name ecsdemo-frontend service up \
    --create-log-groups \
    --target-group-arn <your target group ARN> \
    --private-dns-namespace service \
    --enable-service-discovery \
    --cluster-config ecsdemo \
    --vpc $vpc
    
```

view running containers:
```
ecs-cli compose --project-name ecsdemo-frontend service ps \
    --cluster-config ecsdemo
```

view logs:
```
# substitute your task id from the previous command 
ecs-cli logs --task-id a06a6642-12c5-4006-b1d1-033994580605 \
    --follow --cluster-config ecsdemo
```

scale the tasks:
```
ecs-cli compose --project-name ecsdemo-frontend service scale 3 \
    --cluster-config ecsdemo
ecs-cli compose --project-name ecsdemo-frontend service ps \
    --cluster-config ecsdemo
```

bring up nodejs backend api:
```
cd ~/environment/ecsdemo-nodejs
envsubst <ecs-params.yml.template >ecs-params.yml
ecs-cli compose --project-name ecsdemo-nodejs service up \
    --create-log-groups \
    --private-dns-namespace service \
    --enable-service-discovery 
    --cluster-config ecsdemo

```

bring up crystal backend api:
```
cd ~/environment/ecsdemo-crystal
envsubst <ecs-params.yml.template >ecs-params.yml
ecs-cli compose --project-name ecsdemo-crystal service up \
    --create-log-groups \
    --private-dns-namespace service \
    --enable-service-discovery \
    --cluster-config ecsdemo

```

cleanup:
```
ecs-cli compose --project-name ecsdemo-frontend service down --cluster-config ecsdemo
ecs-cli compose --project-name ecsdemo-nodejs service down --cluster-config ecsdemo
ecs-cli compose --project-name ecsdemo-crystal service down --cluster-config ecsdemo
ecs-cli compose --project-name ecsdemo-frontend service rm
ecs-cli compose --project-name ecsdemo-nodejs service rm
ecs-cli compose --project-name ecsdemo-crystal service rm --delete-namespace

ecs-cli down --force --cluster-config ecsdemo
aws ec2 delete-security-group --group-id $security_group
```


