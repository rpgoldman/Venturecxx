#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from venture import shortcuts

def run_venture_console():
  ripl = shortcuts.make_church_prime_ripl()
  while True:
    sys.stdout.write('>>> ')
    current_line = sys.stdin.readline()
    current_line = current_line.strip()
    # TODO Provide for graceful exit
    if current_line[0] == "(":
      current_line = current_line[1:-1]
    if current_line[0] == "[":
      current_line = current_line[1:-1]
    current_line = current_line.split(" ", 1)
    directive_name = current_line[0].lower()
    content = current_line[1]
    sys.stdout.write('')
    try:
      if (directive_name == "assume"):
        name_and_expression = content.split(" ", 1)
        print ripl.assume(name_and_expression[0], name_and_expression[1])
      elif (directive_name == "predict"):
        name_and_expression = content.split(" ", 1)
        print ripl.predict(content)
      elif (directive_name == "observe"):
        expression_and_literal_value = content.rsplit(" ", 1)
        print ripl.observe(expression_and_literal_value[0], expression_and_literal_value[1])
      elif (directive_name == "infer"):
        ripl.infer(int(content))
        print "The engine has made number of inference iterations: " + content
      elif (directive_name == "forget"):
        ripl.forget(int(content))
        print "You have forgotten the directive #" + content
      elif (directive_name == "report"):
        print ripl.report_value(int(content))
      elif (directive_name == "clear"):
        ripl.clear()
        print "The trace has been cleared."
      else:
        print "Sorry, unknown directive."
    except Exception, err:
      print "Your query has generated an error: " + str(err)

run_venture_console()
