from app import app
from waitress import serve
import logging

if __name__ == '__main__':
    # Initialize basic logging for production
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    logger = logging.getLogger('waitress')
    logger.setLevel(logging.INFO)
    
    print("Starting Waitress Production Server on http://0.0.0.0:5000 ...")
    serve(app, host='0.0.0.0', port=5000)
