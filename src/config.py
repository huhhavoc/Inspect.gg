import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    DEBUG = True
    PORT = 5000
    HOST = '127.0.0.1' # Bind to localhost only for security
    
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    RESULTS_DIR = os.path.join(BASE_DIR, 'results')
    
    # Ensure dirs exist
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
