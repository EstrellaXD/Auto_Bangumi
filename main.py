from module import app
from module import api

import multiprocessing

if __name__ == "__main__":
    multiprocessing.process()

    app.run()
    api.run()

