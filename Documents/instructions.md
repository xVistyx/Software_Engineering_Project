HOW TO INSTALL
Download from github main branch
Chrome extension
- Chrome must be in developer mode for extensions. Settings -> Extensions -> Manage extensions (Top right corner)
- Select Load unpacked
- Select Software_Engineering_Project/Frontend

Backend:
- Check README for instructions on how to install Anaconda
- Setup Conda: conda --version
- Create the environment: conda env create -f environment.yml

- Activate the environment: conda activate LockDownProject
- Verify installation: python --version
conda list
python -m pip check
python -c "import fastapi, uvicorn, pydantic, torch, transformers, peft, accelerate, safetensors; print('Imports successful')"

AI model
- Unzip AISystem/outputs.zip
- Download model and check if it setup correctly: python -u -c "from UserSession.AIEval.AISessionEval import AISessionEval; ai = AISessionEval(); print('AI model loaded successfully')"

HOW TO RUN:

- Run the server: python -m uvicorn main:app --host 127.0.0.1 --port 8000

After this the server should be printing things like:
INFO:     Started server process [81052]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)

After you can use the extension like normal
