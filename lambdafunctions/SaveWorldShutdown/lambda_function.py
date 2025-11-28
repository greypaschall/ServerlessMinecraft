import boto3
import json
import time

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')
cloudwatch = boto3.client('cloudwatch')

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    instance_id = None

    # --- SNS or EventBridge trigger ---
    if 'Records' in event and 'Sns' in event['Records'][0]:
        try:
            sns_msg = json.loads(event['Records'][0]['Sns']['Message'])
            print("SNS Message:", json.dumps(sns_msg))
            if 'Trigger' in sns_msg and 'Dimensions' in sns_msg['Trigger']:
                for d in sns_msg['Trigger']['Dimensions']:
                    if d['name'] == 'InstanceId':
                        instance_id = d['value']
                        break
        except Exception as e:
            print(f"[ERROR] Failed to parse SNS message: {e}")
    elif 'detail' in event and 'instance-id' in event['detail']:
        instance_id = event['detail']['instance-id']

    if not instance_id:
        print("[ERROR] Could not determine instance ID from event payload.")
        return {"status": "error", "reason": "Missing instance ID"}

    print(f"Received stop event for instance {instance_id}")

    # --- If metric uses 'shared', find the running Minecraft instance ---
    if instance_id == "shared":
        print("[INFO] Shared metric detected, locating running Minecraft server instance...")
        reservations = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:MinecraftServer', 'Values': ['True']},
                {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
            ]
        )['Reservations']
        if not reservations:
            print("[ERROR] No running instance with tag MinecraftServer=True found.")
            return {"status": "error", "reason": "No running instance found"}
        instance_id = reservations[0]['Instances'][0]['InstanceId']
        print(f"[OK] Resolved shared metric to instance ID: {instance_id}")

    # --- Tag verification (optional redundancy) ---
    response = ec2.describe_tags(Filters=[
        {'Name': 'resource-id', 'Values': [instance_id]},
        {'Name': 'key', 'Values': ['MinecraftServer']}
    ])
    if not response.get('Tags'):
        print(f"Instance {instance_id} not tagged as MinecraftServer; tagging now...")
        ec2.create_tags(Resources=[instance_id], Tags=[{'Key': 'MinecraftServer', 'Value': 'True'}])

    # --- Run save script via SSM ---
    try:
        print(f"Running mcsave.sh on {instance_id} before shutdown...")
        cmd = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'commands': ["sudo -u ubuntu bash /home/ubuntu/mcsave.sh"]}
        )
        command_id = cmd['Command']['CommandId']

        for i in range(30):  # ~5 minutes
            time.sleep(10)
            result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
            if result['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
                print(f"[OK] Save script finished with status: {result['Status']}")
                break

    except Exception as e:
        print(f"[ERROR] SSM execution failed: {e}")

    # --- Terminate instance ---
    try:
        print(f"Terminating instance {instance_id}...")
        ec2.terminate_instances(InstanceIds=[instance_id])
        print("[OK] Termination command sent.")
    except Exception as e:
        print(f"[ERROR] Could not terminate instance: {e}")

    # --- Delete alarm (cleanup) ---
    alarm_name = f"AutoShutdown-{instance_id}"
    try:
        cloudwatch.delete_alarms(AlarmNames=[alarm_name])
        print(f"[OK] Deleted alarm {alarm_name}")
    except Exception as e:
        print(f"[WARN] Could not delete alarm {alarm_name}: {e}")

    return {"status": "ok", "instance_id": instance_id}
