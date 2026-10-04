from copy import deepcopy
from config.settings import *

DATABASES = deepcopy(DATABASES)
DATABASES['default']['TEST'] = {'NAME': 'test_wims_verify_media'}
