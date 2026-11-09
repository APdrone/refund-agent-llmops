import os
from dotenv import load_dotenv

load_dotenv()

# Evaluator model used by DeepEval metrics
eval_model = os.getenv("EVAL_MODEL", "gpt-6-luna")
