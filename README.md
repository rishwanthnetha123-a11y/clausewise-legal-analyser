# clausewise-legal-analyser
Step-by-Step Guide to Run code.py (ClauseWise Legal Analyzer)

1. Install prerequisites

-   Make sure Python 3.9+ is installed.
-   Open terminal in the folder containing code.py

(optional but recommended) create virtual environment

python -m venv venv

activate it

Windows (PowerShell):

.
env.ps1 # Linux/Mac: source venv/bin/activate

2. Install dependencies

pip install streamlit python-docx PyPDF2 python-dotenv requests

3. Set your Hugging Face API token

-   Get a Hugging Face token from:
    https://huggingface.co/settings/tokens
-   Create a file named .env in the same folder as code.py
-   Add this line into .env (replace with your token):

HF_API_TOKEN=your_hf_token_here

4. Run the app

streamlit run code.py

-   This starts a local web server.
-   Open the link shown (e.g., http://localhost:8501).

5. Use the app

-   Upload a PDF, DOCX, or TXT contract.
-   Click “Analyze Clauses” to see risks, issues, recommendations, tags,
    and summary.

Common Issues

-   “Please set the HF_API_TOKEN” → check your .env file and token
    validity.
-   “403 Forbidden from Hugging Face” → token lacks inference access.
-   “ModuleNotFoundError” → install missing library: pip install .
