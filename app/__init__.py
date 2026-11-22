from .utils.launcher import create_launcher_profiles, check_launcher_files
from .utils import Config

config = Config()

def setup_launcher():
    create_launcher_profiles(config)
    check_launcher_files(config)