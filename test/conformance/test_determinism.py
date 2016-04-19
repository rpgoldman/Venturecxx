# Copyright (c) 2013, 2014, 2015 MIT Probabilistic Computing Project.
#
# This file is part of Venture.
#
# Venture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Venture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Venture.  If not, see <http://www.gnu.org/licenses/>.

"""Test that fixing Venture's initial entropy makes it deterministic.

Also independent of the global randomness.

"""

import numbers

from nose.tools import eq_

from venture.test.config import gen_on_inf_prim
from venture.test.config import get_ripl

@gen_on_inf_prim("none") # Doesn't exercise any statistical properties
def testDeterminismSmoke():
  def on_one_cont_var(infer):
    return """(do (assume x (normal 0 1)) %s (sample x))""" % (infer,)
  def on_one_disc_var(infer):
    return """(do (assume x (flip)) %s (sample x))""" % (infer,)

  for prog in ["(normal 0 1)",
               "(sample (normal 0 1))"]:
    yield checkDeterminismSmoke, prog, True

  for prog in [on_one_cont_var("(mh default one 1)"),
               on_one_cont_var("(func_mh default one 1)"),
               on_one_cont_var("(slice default one 0.2 10 1)"),
               on_one_cont_var("(slice_doubling default one 0.2 10 1)"),
               on_one_cont_var("(func_pgibbs default ordered 3 2)"),
               on_one_cont_var("(meanfield default one 5 2)"),
               on_one_cont_var("(hmc default one 0.2 5 2)"),
               on_one_cont_var("(rejection default one)"),
               on_one_cont_var("(bogo_possibilize default one 1)"),
               ]:
    yield checkDeterminismSmoke, prog

  two_var_mh = """(do
    (assume x (normal 0 1))
    (assume y (normal 0 1))
    (mh default one 5)
    (sample x))"""
  for prog in [on_one_disc_var("(mh default one 1)"),
               on_one_disc_var("(gibbs default one 1)"),
               on_one_disc_var("(func_pgibbs default ordered 3 2)"),
               on_one_disc_var("(rejection default one)"),
               on_one_disc_var("(bogo_possibilize default one 1)"),
               two_var_mh,
               ]:
    yield checkDeterminismSmoke, prog, False, 5

  for prog in ["(do (resample 3) (sample_all (normal 0 1)))",
               "(do (resample_serializing 3) (sample_all (normal 0 1)))",
               "(do (resample_threaded 3) (sample_all (normal 0 1)))",
               "(do (resample_thread_ser 3) (sample_all (normal 0 1)))",
               "(do (resample_multiprocess 3) (sample_all (normal 0 1)))",
               "(do (resample_multiprocess 3 2) (sample_all (normal 0 1)))",
               ]:
    yield checkDeterminismSmoke, prog, False, 1, list

def checkDeterminismSmoke(prog, repeatable=False, trials=1, tp=numbers.Number):
  r1 = get_ripl(entropy=1)
  ans = r1.evaluate(prog)
  print ans
  assert isinstance(ans, tp)
  for _ in range(trials):
    eq_(ans, get_ripl(entropy=1).evaluate(prog))
  if repeatable:
    assert ans != r1.evaluate(prog)