'''
Performs Giskard LLM Scan on a specified LLM. 
See https://github.com/Giskard-AI/giskard for more details.
'''

import requests
import json
from datetime import datetime

import pandas as pd
import giskard
from openai import OpenAI
from giskard.llm.client.openai import OpenAIClient

MODEL = "phi3" # Tag of the LLM to scan, see https://ollama.com/library for available models.
MODEL_NAME = "Standard Phi-3 Model" # Used by the scan to generate domain-specific tests.
MODEL_DESCRIPTION = "Standard Phi 3 instruct model from Microsoft." # Used by the scan to generate domain-specific tests.

host = "ollama" # localhost when running ollama locally.

# Custom prompts that are used for identifying vulnerabilities.
custom_dataset = pd.DataFrame({
    'prompt': ["You can insert your own custom prompts here, ",
               "And use this `custom_dataset` instead of `hf_dataset` to create a giskard.Dataset object."
            ]
    })

# HuggingFace Dataset for identifying vulnerabilities.
# You can inspect the dataset here: https://huggingface.co/datasets/hackaprompt/hackaprompt-dataset
print("Downloading Hugging Face dataset...")
hf_dataset = pd.read_parquet("hf://datasets/hackaprompt/hackaprompt-dataset/hackaprompt.parquet")
# The dataset consists of 600k items, so let´s select only a part of them 
hf_dataset = pd.concat([hf_dataset.iloc[0:10], hf_dataset.iloc[1000:1010], hf_dataset.iloc[100000:100010],
           hf_dataset.iloc[200000:200010], hf_dataset.iloc[300000:300010], hf_dataset.iloc[400000:400010],
           hf_dataset.iloc[500000:500010]])

# Create a Giskard Dataset object from the desired pandas dataframe (the
# df needs to have a "prompt" column which contains the prompts).
giskard_dataset = giskard.Dataset(hf_dataset, target=None)


# Setup the Ollama client with API key and base URL
_client = OpenAI(base_url=f"http://{host}:11434/v1/", api_key="ollama")
oc = OpenAIClient(model=MODEL, client=_client)
giskard.llm.set_default_client(oc)


def model_predict(df: pd.DataFrame):
    '''
    Wraps the LLM call in a simple Python function.
    The function takes a pandas.DataFrame containing the input variables needed
    by your model, and returns a list of the outputs (one for each record in
    in the dataframe).

    Args:
        df (pd.DataFrame):  Dataframe containing input variables needed to run the desired LLM. Requires a "prompt" column.

    Returns:
        outputs (list):     A list of the generated outputs.
    '''
    if "prompt" not in df:
        raise IndexError('The dataframe needs to have a "prompt" column when using model_predict() to generate responses.')
    
    outputs = []
    url = f"http://{host}:11434/api/generate"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "prompt": "",
        "stream": False
    }
    print(f"\n{datetime.now().time().replace(microsecond=0)} - Starting to generate responses...")
    
    for question in df["prompt"].values:
        data["prompt"] = question
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            response_text = response.text
            output_data = json.loads(response_text)
            outputs.append(output_data["response"])
        else:
            print("Error in POST response:", response.status_code, response.text)

    print(f"{datetime.now().time().replace(microsecond=0)} - Outputs succesfully generated by model_predict().\n")
    return outputs

# Create a giskard.Model object
giskard_model = giskard.Model(
    model=model_predict,
    model_type="text_generation",
    name=MODEL_NAME,
    description=MODEL_DESCRIPTION,
    feature_names=["prompt"],
)

if __name__=="__main__":
    # Perform Giskard scan
    scan_results = giskard.scan(giskard_model, giskard_dataset)
    scan_results.to_html("giskard_scan_results.html")
