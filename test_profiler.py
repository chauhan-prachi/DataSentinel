from pprint import pprint

from core.services.quality.profiler import DatasetProfiler


profiler = DatasetProfiler()

profile = profiler.profile_csv("data/customers.csv")

pprint(profile)