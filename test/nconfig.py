from venture.shortcuts import make_lite_church_prime_ripl

global config
config = {}

config["num_samples"] = 1000
config["num_transitions_per_sample"] = 5
config["should_reset"] = False
config["get_ripl"] = make_lite_church_prime_ripl
config["global_reporting_threshold"] = 0.001
config["kernel"] = "mh"
config["scope"] = "default"
config["block"] = "one"
