import pdb
from nose.tools import assert_equals

def assertTorus(scaffold):
  for node,regenCount in scaffold.regenCounts.iteritems(): 
    if regenCount != 0: pdb.set_trace()

def assertTrace(trace,scaffold):
  for node in scaffold.regenCounts:
    assert trace.valueAt(node) is not None

def assertSameScaffolds(scaffoldA,scaffoldB):
  print "----- from regen -----"
  scaffoldA.show()
  print "----- from construct -----"
  scaffoldB.show()
  assert_equals(len(scaffoldA.regenCounts),len(scaffoldB.regenCounts))
  assert_equals(len(scaffoldA.absorbing),len(scaffoldB.absorbing))
  assert_equals(len(scaffoldA.aaa),len(scaffoldB.aaa))
  assert_equals(len(scaffoldA.border),len(scaffoldB.border))
  for node in scaffoldA.regenCounts:
    if scaffoldA.getRegenCount(node) != scaffoldB.getRegenCount(node):
      pdb.set_trace()
    assert_equals(scaffoldA.getRegenCount(node),scaffoldB.getRegenCount(node))

