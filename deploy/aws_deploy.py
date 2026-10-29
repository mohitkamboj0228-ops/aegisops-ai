"""Deploy a built AegisOps release using the caller's temporary AWS credentials."""
import argparse, hashlib, json, re, shlex, sys, tempfile, time
from pathlib import Path
from package import package


def deploy(args):
    import boto3
    from botocore.exceptions import ClientError
    session=boto3.Session(region_name=args.region)
    identity=session.client('sts').get_caller_identity()
    print('Deploying to AWS account',identity['Account'],'region',args.region,flush=True)
    ec2=session.client('ec2')
    subnet=ec2.describe_subnets(SubnetIds=[args.subnet])['Subnets'][0]
    if subnet['VpcId']!=args.vpc: raise ValueError('Subnet does not belong to the supplied VPC')
    cf=session.client('cloudformation');ssm=session.client('ssm');s3=session.client('s3')
    template=(Path(__file__).parent/'aws-stack.yaml').read_text()
    with tempfile.TemporaryDirectory() as tmp:
        artifact=Path(tmp)/'release.zip';release=package(artifact)
        key='releases/'+hashlib.sha256(artifact.read_bytes()).hexdigest()+'.zip'
        s3.upload_file(str(artifact),args.bucket,key,ExtraArgs={'ServerSideEncryption':'AES256'})
    try:
        existing=cf.describe_stacks(StackName='aegisops-app')['Stacks'][0]
        exists=True
    except ClientError as e:
        if e.response['Error']['Code']!='ValidationError' or 'does not exist' not in str(e): raise
        exists=False
    if exists:
        previous={p['ParameterKey']:p['ParameterValue'] for p in existing['Parameters']}
        if previous['VpcId']!=args.vpc or previous['SubnetId']!=args.subnet:
            raise ValueError('Changing VPC/subnet can replace the instance and lose local data. Use a separate migration process.')
        ami=previous['AmiId']
    else:
        ami=ssm.get_parameter(Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64')['Parameter']['Value']
    params=[{'ParameterKey':k,'ParameterValue':v} for k,v in {
        'VpcId':args.vpc,'SubnetId':args.subnet,'InstanceProfile':args.profile,
        'ArtifactBucket':args.bucket,'ArtifactKey':key,'BedrockModelArn':args.model,'AmiId':ami}.items()]
    try:
        if exists:
            cf.update_stack(StackName='aegisops-app',TemplateBody=template,Parameters=params)
            waiter='stack_update_complete'
        else:
            cf.create_stack(StackName='aegisops-app',TemplateBody=template,Parameters=params)
            waiter='stack_create_complete'
        cf.get_waiter(waiter).wait(StackName='aegisops-app',WaiterConfig={'Delay':10,'MaxAttempts':90})
    except ClientError as e:
        if not (exists and 'No updates are to be performed' in str(e)): raise
    stack=cf.describe_stacks(StackName='aegisops-app')['Stacks'][0]
    outputs={x['OutputKey']:x['OutputValue'] for x in stack['Outputs']}
    instance=outputs['InstanceId'];print('Waiting for SSM on',instance,flush=True)
    for _ in range(90):
        info=ssm.describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[instance]}])['InstanceInformationList']
        if info and info[0]['PingStatus']=='Online':break
        time.sleep(10)
    else:raise RuntimeError('Instance did not register with SSM. Check egress, instance profile and SSM agent.')
    # Wait for cloud-init to finish before updating/installing. Never accept arbitrary commands from users or AI.
    env='AWS_REGION='+args.region+'\nAEGIS_AI_PROVIDER='+('bedrock' if args.model else 'disabled')+'\nAEGIS_AI_MODEL='+args.model+'\nAEGIS_DB=/var/lib/aegis/aegis.db\nAEGIS_HOST=127.0.0.1\n'
    command='\n'.join([
        'set -euo pipefail',
        'cloud-init status --wait',
        'dnf install -y python3 python3-pip unzip awscli2',
        'printf %s '+shlex.quote(env)+' > /etc/aegisops.env',
        'chmod 600 /etc/aegisops.env',
        'work=$(mktemp -d)',
        'trap \'rm -rf "$work"\' EXIT',
        'aws s3 cp '+shlex.quote('s3://'+args.bucket+'/'+key)+' "$work/release.zip" --region '+shlex.quote(args.region),
        'printf "%s  %s\\n" '+shlex.quote(key.split('/')[1].removesuffix('.zip'))+' "$work/release.zip" | sha256sum -c -',
        'unzip -q "$work/release.zip" -d "$work/source"',
        'bash "$work/source/deploy/install.sh"',
    ])
    command_id=ssm.send_command(InstanceIds=[instance],DocumentName='AWS-RunShellScript',Parameters={'commands':[command],'executionTimeout':['900']},TimeoutSeconds=900)['Command']['CommandId']
    for _ in range(120):
        try:result=ssm.get_command_invocation(CommandId=command_id,InstanceId=instance)
        except ssm.exceptions.InvocationDoesNotExist:time.sleep(5);continue
        status=result['Status']
        if status=='Success':
            print('Verified application health. Release:',release)
            print(outputs['Access']);return
        if status not in ('Pending','InProgress','Delayed'):
            raise RuntimeError('Deployment command failed: '+status+'. Inspect SSM command '+command_id+' and /var/log/aegis-bootstrap.log.')
        time.sleep(10)
    raise RuntimeError('Deployment verification timed out; inspect SSM command '+command_id)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('region','bucket','vpc','subnet','profile'):p.add_argument('--'+flag,required=True)
    p.add_argument('--model',default='');a=p.parse_args()
    if not re.fullmatch(r'[a-z]{2}(?:-gov)?-[a-z]+-\d',a.region):p.error('Invalid region')
    if not re.fullmatch(r'[a-z0-9.-]{3,63}',a.bucket):p.error('Invalid bucket')
    if not re.fullmatch(r'vpc-[a-f0-9]+',a.vpc) or not re.fullmatch(r'subnet-[a-f0-9]+',a.subnet):p.error('Invalid VPC/subnet')
    if not re.fullmatch(r'[A-Za-z0-9+=,.@_-]+',a.profile):p.error('Invalid instance profile')
    if a.model and not re.fullmatch(r'arn:aws:bedrock:[a-z0-9-]+:[0-9]*:(foundation-model|inference-profile)/[A-Za-z0-9.:-]+',a.model):p.error('Invalid Bedrock ARN')
    deploy(a)
