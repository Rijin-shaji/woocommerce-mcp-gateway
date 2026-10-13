from fastapi import FastAPI

app = FastAPI(title="WooCommerce MCP Gateway")


@app.get("/")
def home():
    return {"message": "WooCommerce MCP Gateway is running!"}


@app.get("/health")
def health():
    return {"status": "healthy"}


