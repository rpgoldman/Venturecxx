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

import math
import numbers
import random

import numpy as np
import numpy.random as npr
import numpy.linalg as npla
import scipy.special as ss

# This one is from http://stackoverflow.com/questions/1167617/in-python-how-do-i-indicate-im-overriding-a-method
def override(interface_class):
  def overrider(method):
    assert method.__name__ in dir(interface_class)
    return method
  return overrider

def extendedLog(x): return math.log(x) if x > 0 else float("-inf")

def normalizeList(seq):
  denom = sum(seq)
  if denom > 0: return [ float(x)/denom for x in seq]
  else:
    # Treat all impossible options as equally impossible.
    n = float(len(seq))
    return [1.0/n for x in seq]

def simulateCategorical(ps,np_rng,os=None):
  if os is None: os = range(len(ps))
  ps = normalizeList(ps)
  return os[np_rng.multinomial(1,ps).argmax()]

def logDensityCategorical(val,ps,os=None):
  if os is None: os = range(len(ps))
  ps = normalizeList(ps)
  # TODO This should work for Venture Values while the comparison is
  # done by identity and in the absence of observations; do I want to
  # override the Python magic methods for VentureValues?
  p = 0
  for (pi, oi) in zip(ps, os):
    if oi == val:
      p += pi
  if p == 0:
    return float('-inf')
  return math.log(p)

def logDensityCategoricalSequence(weights, counts):
  """The log probability that repeated application of a categorical with
  the given weights will give a sequence of results described by the
  given counts (all such sequences have the same probability).

  weight-count alignment is positional, abstracting away from any
  underlying objects.  In particular, any collapsing on equal objects
  should be done before calling this.
  """
  def term(w, c):
    if c == 0: return 0 # Even if w == 0
    if w == 0: return float('-inf')
    return np.log(w) * c
  return sum(term(w, c) for (w, c) in zip(weights, counts))

def simulateDirichlet(alpha, np_rng): return np_rng.dirichlet(alpha)

def logDensityDirichlet(theta, alpha):
  theta = np.array(theta)
  alpha = np.array(alpha)

  return ss.gammaln(sum(alpha)) - sum(ss.gammaln(alpha)) + np.dot((alpha - 1).T, np.log(theta).T)

# CONSIDER why not use itertools.prod?
def cartesianProduct(original):
  if len(original) == 0: return [[]]
  elif len(original) == 1: return [[x] for x in original[0]]
  else:
    firstGroup = original[0]
    recursiveProduct = cartesianProduct(original[1:])
    return [ [v] + vs for v in firstGroup for vs in recursiveProduct]

def logaddexp(items):
  "Apparently this was added to scipy in a later version than the one installed on my machine.  Sigh."
  the_max = max(items)
  if the_max > float("-inf"):
    return the_max + math.log(sum(math.exp(item - the_max) for item in items))
  else:
    return the_max # Don't want NaNs from trying to correct from the maximum

def log_domain_even_out(items, n=None):
  "Return a list of n equal numbers whose logsumexp equals the logsumexp of the inputs."
  if n is None:
    n = len(items)
  answer = logaddexp(items) - math.log(n)
  return [answer for _ in range(n)]

def logWeightsToNormalizedDirect(logs):
  "Converts an unnormalized categorical distribution given in logspace to a normalized one given in direct space"
  the_max = max(logs)
  if the_max > float("-inf"):
    # Even if the logs include some -inf values, math.exp will produce
    # zeros there and it will be fine.
    return normalizeList([math.exp(log - the_max) for log in logs])
  else:
    # If all the logs are -inf, force 0 instead of NaN.
    return [0 for _ in logs]

def sampleLogCategorical(logs, np_rng):
  "Samples from an unnormalized categorical distribution given in logspace."
  the_max = max(logs)
  if the_max > float("-inf"):
    return simulateCategorical([math.exp(log - the_max) for log in logs],
      np_rng, os=None)
  else:
    # normalizeList, as written above, will actually do the right
    # thing with this, namely treat all impossible options as equally
    # impossible.
    return simulateCategorical([0 for _ in logs], np_rng, os=None)

def numpy_force_number(answer):
  if isinstance(answer, numbers.Number):
    return answer
  else:
    return answer[0,0]

# TODO Change it to use the scipy function when Venture moves to requiring scipy 0.14+
def logDensityMVNormal(x, mu, sigma):
  answer =  -.5*np.dot(np.dot(x-mu, npla.inv(sigma)), np.transpose(x-mu)) \
            -.5*len(sigma)*np.log(2 * np.pi)-.5*np.log(abs(npla.det(sigma)))
  return numpy_force_number(answer)

def careful_exp(x):
  try:
    return math.exp(x)
  except OverflowError:
    if x > 0: return float("inf")
    else: return float("-inf")

def logistic(x): return 1 / (1 + careful_exp(-x))

def T_logistic(x):
  # This should be derivable from the above by AD, but here I use the
  # identity d logistic(x) / dx = logistic(x) * (1 - logistic(x))
  logi_x = logistic(x)
  return (logi_x, logi_x * (1 - logi_x))

def log_logistic(x):
  if x < -40:
    # Because 1 + exp(40+) = exp(40+) in IEEE-64, and I don't want the
    # +inf that will come from exp(400+)
    return x
  else: return math.log(logistic(x))

def d_log_logistic(x):
  # This should be derivable from the above by AD.
  # Perhaps this could be improved upon by analysis, due to the usual
  # derivative of approximation problem.
  if x < -40:
    return 1
  else:
    (logi_x, dlogi_x) = T_logistic(x)
    return (1/logi_x) * dlogi_x

def logit(x):
  # TODO Check the numeric analysis of this
  return extendedLog(x / (1 - x))

class FixedRandomness(object):
  """A Python context manager for executing (stochastic) code repeatably
against fixed randomness.

  Caveat: If the underlying code attempts to monkey with the state of
  the random number generator (other than by calling it) that
  monkeying will be suppressed, and not propagated to its caller. """

  def __init__(self, py_rng=random.Random(), np_rng=npr.RandomState()):
    self.py_rng = py_rng
    self.np_rng = np_rng
    self.pyr_state = py_rng.getstate()
    self.numpyr_state = np_rng.get_state()
    py_rng.jumpahead(py_rng.randint(1,2**31-1))
    np_rng.seed(py_rng.randint(1,2**31-1))

  def __enter__(self):
    self.cur_pyr_state = self.py_rng.getstate()
    self.cur_numpyr_state = self.np_rng.get_state()
    self.py_rng.setstate(self.pyr_state)
    self.np_rng.set_state(self.numpyr_state)

  def __exit__(self, _type, _value, _backtrace):
    self.py_rng.setstate(self.cur_pyr_state)
    self.np_rng.set_state(self.cur_numpyr_state)
    return False # Do not suppress any thrown exception

# raise is a statement and can't be used in a lambda :(
def raise_(e): raise e
