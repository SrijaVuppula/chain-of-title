"""Environment/config loader. Implemented: BUILD_PLAN.md Day 2 (Aug 3)"""
import os
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
IBM_WATSONX_APIKEY = os.getenv("IBM_WATSONX_APIKEY")
IBM_WATSONX_REGION = os.getenv("IBM_WATSONX_REGION")
