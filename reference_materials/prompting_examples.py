import json


def make_inference_prompt(instructions, responses):
    responses_json = {str(i): response for i, response in enumerate(responses)}
    prompt = f"""{instructions}
Responses = {json.dumps(responses_json, indent=4)}

Do not return any explanation or pre-amble.
Only return the scores in the format specified.

Return scores in this format:
{{
    "0": <score category>,
    "1": <score category>,
    ...
    "n": <score category>
}}
"""
    return prompt


def get_score_json(response):
    response = response.replace("```json", "").replace("```", "").strip()
    score_json = json.loads(response)
    return score_json