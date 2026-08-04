from fastapi import FastAPI

from wellmanifest.server import create_app

# Mount the complete runtime as a backend service.
app: FastAPI = create_app()
