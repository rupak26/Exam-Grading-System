import yaml
import urllib.parse
from pathlib import Path


##################################
#ENVIRONMENT =  "prod"
ENVIRONMENT =  "dev"
##################################

def load_config(file_path , environment = None):
    try:
        with open(file_path , "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing the YAML configuration file: {e}") 

    if environment not in config:
        raise ValueError(f"Environment '{environment}' not found in the config file.")

    return config[environment]    



BASE_DIR = Path(__file__).resolve().parent
    
CONFIG = load_config(BASE_DIR / "config.yml" , ENVIRONMENT)


DB_NAME = CONFIG['db']['name'] 
DB_USER = CONFIG['db']['user']
DB_PASSWORD = CONFIG['db']['password']
DB_PORT = CONFIG['db']['port'] 
DB_HOST = CONFIG['db']['host']
LOG_DIRECTORY = CONFIG['log']['directory']
LOG_NAME = CONFIG['log']['name']
LOG_SIZE = CONFIG['log']['size']

DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"