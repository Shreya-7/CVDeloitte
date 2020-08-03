#app.wsgi
import sys
sys.path.insert(0, '/var/www/html/cvdeloitte')

from app import app as application
