FROM python:3.11-slim
 
WORKDIR /app
 
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
 
COPY . /app
 
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]