from retrieval import Retrieval
from reporting import Reporting


class Pipeline(object):
    def __init__(self):
        self.retrieval = Retrieval()
        self.reporting = Reporting()

    def run(self):
        self.retrieval.run()
        self.reporting.run()
