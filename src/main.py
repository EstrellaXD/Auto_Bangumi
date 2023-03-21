from module import app
from module import api

import threading

if __name__ == "__main__":
    t = threading.Thread(target=app.run)
    t.daemon = True
    t.start()
    
    # API
    api.run()

