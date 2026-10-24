FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build the database from the CSV files
RUN python src/database.py && python src/loadDataToDatabase.py && python src/buildCityFeatures.py && python src/clusterCities.py && python src/classifyPriceTier.py

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
