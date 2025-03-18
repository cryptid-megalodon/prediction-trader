import json
import dotenv
import os
import requests
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content

import prompts

env = dotenv.dotenv_values(".env")
genai.configure(api_key=env["GEMINI_API_KEY"])

regions = [
  "us-central1",
	"northamerica-northeast1",
	"southamerica-east1",
	"us-east1",
	"us-east4",
	"us-east5",
	"us-south1",
	"us-west1",
	"us-west4",
	"asia-east1",
	"asia-east2",
	"asia-northeast1",
	"asia-northeast3",
	"asia-south1",
	"asia-southeast1",
	"australia-southeast1",
	"europe-central2",
	"europe-north1",
	"europe-southwest1",
	"europe-west1",
	"europe-west2",
	"europe-west3",
	"europe-west4",
	"europe-west6",
	"europe-west8",
	"europe-west9",
	"me-central1",
	"me-central2",
	"me-west1"
]

def create_report(market_description, cache=None):
  """Creates a report based on the provided market description using the Perplexity AI API.
  
  Args:
      market_description (str): The description of the market to generate the report for.
  
  Returns:
      str: The generated report response in an uncleaned and unverified JSON string."""

  if cache:
    print("Checking for cached report...")
    cache_result = cache.get(market_description)
    if cache_result:
      print("Cached report found!")
      return cache_result
    else:
      print("No cached report found. Generating new report...")

  url = "https://api.perplexity.ai/chat/completions"
  payload = {
    "model": "sonar-pro",
    "messages": [
      {
        "role": "system",
        "content": prompts.report_system_prompt,
      },
      {
        "role": "user",
        "content": prompts.report_content_template(market_description),
      }
    ],
      "max_tokens": "65536",
      "temperature": 0.2,
      "top_p": 0.3,
      "search_domain_filter": [],
      "return_images": False,
      "return_related_questions": False,
      "search_recency_filter": "month",
      "top_k": 40,
      "stream": False,
      "frequency_penalty": 1.1,
      "response_format": None
  }

  headers = {
    "Authorization": f"Bearer {env['PERPLEXITY_API_KEY']}",
    "Content-Type": "application/json"
  }

  print("Writing report...")
  report_response = requests.request("POST", url, json=payload, headers=headers, timeout=120)
  if report_response.status_code != 200:
    print(f"Error: {report_response.status_code} - {report_response.text}")
    exit(1)
  report = report_response.json()["choices"][-1]["message"]["content"]
  print("Report:", report)
  if cache:
    print("caching report...")
    cache.set(market_description, report)
  return report

def create_market_prediction(report, market_description):
  """Creates a market prediction based on the provided report and market description.
  
  Args:
      report (str): The report containing the information to generate the prediction.
      market_description (str): The description of the market to generate the prediction for.
  
  Returns:
      str: The generated prediction response in an uncleaned and unverified json string."""

  analysis_generation_config = {
    "temperature": 0.2,
    "top_p": 0.1,
    "top_k": 40,
    "max_output_tokens": 65536,
    "response_mime_type": "text/plain",
  }

  prediction_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-thinking-exp-01-21",
    # model_name="gemini-2.0-flash",
    generation_config=analysis_generation_config,
    system_instruction=prompts.prediction_system_prompt,
  )

  prediction_chat_session = prediction_model.start_chat()

  print("Starting analysis...")
  prediction_response = prediction_chat_session.send_message(
  prompts.prediction_content_template(report, market_description))
  print("Analysis:", prediction_response.text)
  return prediction_response.text

def llm_parse_raw_prediction(prediction):
  """Parses the analysis text and returns a JSON object with the following structure:
  - `reasoning`: string containing the reasoning for the prediction.
  - `probability`: float representing the estimated probability of the prediction, between 0 and 1.
  - `uncertainty`: object containing:
    - `lower_bound`: float representing the lower bound of the confidence interval, between 0 and 1.
    - `upper_bound`: float representing the upper bound of the confidence interval, between 0 and 1.
    - `confidence_level`: float representing the confidence level of the prediction, between 0 and 1.
  - `model_confidence`: float representing the model's confidence in the prediction, between 0 and 1."""

  analysis_generation_config = {
    "temperature": 0.0,
    "top_p": 0.1,
    "top_k": 20,
    "max_output_tokens": 8192,
    "response_schema": content.Schema(
      type = content.Type.OBJECT,
      enum = [],
      required = ["reasoning", "probability", "uncertainty", "model_confidence"],
      properties = {
        "probability": content.Schema(
          type = content.Type.NUMBER,
        ),
        "uncertainty": content.Schema(
          type = content.Type.OBJECT,
          enum = [],
          required = ["lower_bound", "upper_bound", "confidence_level"],
          properties = {
            "lower_bound": content.Schema(
              type = content.Type.NUMBER,
            ),
            "upper_bound": content.Schema(
              type = content.Type.NUMBER,
            ),
            "confidence_level": content.Schema(
              type = content.Type.NUMBER,
            ),
          },
        ),
        "model_confidence": content.Schema(
          type = content.Type.NUMBER,
        ),
        "reasoning": content.Schema(
          type = content.Type.STRING,
        ),
      },
    ),
    "response_mime_type": "application/json",
  }
  json_parse_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-lite-preview-02-05",
    generation_config=analysis_generation_config,
    system_instruction=prompts.json_parse_system_prompt,
  )
  json_parse_chat_session = json_parse_model.start_chat()
  output_response = json_parse_chat_session.send_message(
      prompts.json_parse_content_template(prediction))
  return output_response.text

def clean_parse_raw_prediction(raw_prediction):
  """Cleans and parses the raw prediction output, handling any JSON parsing errors by falling back to LLM parsing.
  
  Args:
      raw_prediction (str): The raw prediction output to be cleaned and parsed.
  
  Returns:
      dict: A dictionary containing the parsed prediction data, or an empty dictionary if parsing fails."""
  try:
    clean_json = raw_prediction.replace('```json', '').replace('```', '').strip()
    prediction_json = json.loads(clean_json)
  except (ValueError, json.decoder.JSONDecodeError) as e:
    print("Error: Market Analysis did not have JSON-only output. Falling back to LLM Parsing:", e)
  try:
    prediction_json = json.loads(llm_parse_raw_prediction(raw_prediction))
  except json.decoder.JSONDecodeError as e:
    print("Error: LLM Parsing Failed. Invalid JSON output. Error:", e)
    return {}
  return prediction_json

def create_prediction(market_description, cache=None):
  """Creates a prediction for a given market description.
    
  Args:
      market_description (str): Description of the prediction market to analyze
        
  Returns:
      str: JSON string containing:
          - reasoning (str): Summary of prediction reasoning
          - probability (float): Estimated probability between 0-1
          - uncertainty (object): Contains confidence interval data
              - lower_bound (float): Lower bound of estimate between 0-1
              - upper_bound (float): Upper bound of estimate between 0-1
              - confidence_level (float): Confidence level between 0-1
          - model_confidence (float): Model's confidence in prediction between 0-1
  """
  report = create_report(market_description, cache=cache)
  if cache:
    print("Checking for cached prediction...")
    cache_result = cache.get(report)
    if cache_result:
      print("Cached prediction found!")
      return cache_result
    else:
      print("No cached prediction found. Generating new prediction...")

  prediction_raw_ouput = create_market_prediction(report, market_description)
  cleaned_prediction = clean_parse_raw_prediction(prediction_raw_ouput)
  if cache:
    print("caching parsed prediction...")
    cache.set(report, cleaned_prediction)
  return cleaned_prediction
