import math
import json
import random
import textwrap

import boto3
import pandas as pd


bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
inference_profile_arn = 'arn:aws:bedrock:us-east-1:457209544455:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0'

def generate_response(prompt):
    request_payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt}]
            }
        ]
    }
    response = bedrock_runtime.invoke_model(
        modelId=inference_profile_arn,
        body=json.dumps(request_payload))
    response_body = response['body'].read()
    text = json.loads(response_body)
    answer = text['content'][0]['text']
    return answer


prompt = """Tell me some interesting facts about the number 42."""
print(generate_response(prompt))
