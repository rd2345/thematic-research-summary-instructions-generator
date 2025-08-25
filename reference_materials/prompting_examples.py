import json


def make_inference_prompt(instructions, responses):
    responses_json = {str(i): response for i, response in enumerate(responses)}
    prompt = f"""{instructions}
Responses = {json.dumps(responses_json, indent=4)}

Do not return any explanation or pre-amble.
Only return the summaries in the format specified.

Return summaries in this format:
{{
    "0": <summary type>,
    "1": <summary type>,
    ...
    "n": <summary type>
}}
"""
    return prompt


def get_summary_json(response):
    response = response.replace("```json", "").replace("```", "").strip()
    summary_json = json.loads(response)
    return summary_json