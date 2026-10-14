# CloudLap - containerized server
# Note: the GUI launcher (launcher.pyw) is Windows-only and not part of this image.
# This builds the MCP server itself so it can run anywhere Docker runs.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py totp.py config.example.json ./

# Default config - mount your own config.json over this at runtime
RUN cp config.example.json config.json

EXPOSE 8787

CMD ["python", "server.py"]
