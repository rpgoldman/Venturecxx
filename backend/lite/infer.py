import random
import math
from consistency import assertTorus,assertTrace
from omegadb import OmegaDB
from regen import regenAndAttach
from detach import detachAndExtract
from scaffold import constructScaffold
from node import ApplicationNode, OutputNode
from lkernel import VariationalLKernel
from utils import sampleCategorical

def mixMH(trace,indexer,operator):
  index = indexer.sampleIndex(trace)
  rhoMix = indexer.logDensityOfIndex(trace,index)
  logAlpha = operator.propose(trace,index) # Mutates trace and possibly operator
  xiMix = indexer.logDensityOfIndex(trace,index)

  if math.log(random.random()) < xiMix + logAlpha - rhoMix:
    operator.accept() # May mutate trace
  else:
    operator.reject() # May mutate trace

class BlockScaffoldIndexer(object):
  def __init__(self,scope,block):
    self.scope = scope
    self.block = block

  def sampleIndex(self,trace):
    if self.scope == "default":
      if not(self.block == "one"):
        raise Exception("INFER custom blocks for default scope not yet implemented (%r)" % block)
      pnode = [[trace.samplePrincipalNode()]]
      return constructScaffold(trace,pnode)
    else:
      if self.block == "one":
        goalBlock = trace.sampleBlock(self.scope)
        pnodes = [trace.scopes[self.scope][goalBlock]]
      elif self.block == "all":
        blocks = trace.blocksInScope(self.scope)
        pnodeSets = [trace.scopes[self.scope][block] for block in blocks]
        pnodes = [set().union(*pnodeSets)]
      elif self.block == "ordered":
        blocks = trace.blocksInScope(self.scope)
        pnode = [trace.scopes[self.scope][block] for block in blocks]
      else:
        pnodes = [trace.scopes[self.scope][self.block]]
      return constructScaffold(trace,pnodes)

  def logDensityOfIndex(self,trace,scaffold):
    if self.scope == "default":
      if not(self.block == "one"):
        raise Exception("INFER custom blocks for default scope not yet implemented (%r)" % block)
      return trace.logDensityOfPrincipalNode(None) # the actual principal node is irrelevant
    else:
      if self.block == "one":
        return trace.logDensityOfBlock(self.scope,None) # The actual block in irrelevant
      elif self.block == "all":
        return 0
      else:
        return 0

class MHOperator(object):
  def propose(self,trace,scaffold):
    self.trace = trace
    self.scaffold = scaffold
    rhoWeight,self.rhoDB = detachAndExtract(trace,scaffold.border[0],scaffold)
    assertTorus(scaffold)
    xiWeight = regenAndAttach(trace,scaffold.border[0],scaffold,False,self.rhoDB,{})
    return xiWeight - rhoWeight

  def accept(self): pass
  def reject(self):
    detachAndExtract(self.trace,self.scaffold.border[0],self.scaffold)
    assertTorus(self.scaffold)
    regenAndAttach(self.trace,self.scaffold.border[0],self.scaffold,True,self.rhoDB,{})


def registerVariationalLKernels(trace,scaffold):
  hasVariational = False
  for node in scaffold.regenCounts:
    if isinstance(node,ApplicationNode) and \
       not trace.isConstrainedAt(node) and \
       trace.pspAt(node).hasVariationalLKernel() and \
       not scaffold.isResampling(node.operatorNode):
      scaffold.lkernels[node] = trace.pspAt(node).getVariationalLKernel(trace,node)
      hasVariational = True
  return hasVariational

class MeanfieldOperator(object):
  def __init__(self,numIters,stepSize):
    self.numIters = numIters
    self.stepSize = stepSize
    self.delegate = None

  def propose(self,trace,scaffold):
    self.trace = trace
    self.scaffold = scaffold
    if not registerVariationalLKernels(trace,scaffold):
      self.delegate = MHOperator()
      return self.delegate.propose(trace,scaffold)
    _,self.rhoDB = detachAndExtract(trace,scaffold.border[0],scaffold)
    assertTorus(scaffold)

    for i in range(self.numIters):
      gradients = {}
      gain = regenAndAttach(trace,scaffold.border[0],scaffold,False,OmegaDB(),gradients)
      detachAndExtract(trace,scaffold.border[0],scaffold)
      assertTorus(scaffold)
      for node,lkernel in scaffold.lkernels.iteritems():
        if isinstance(lkernel,VariationalLKernel):
          assert node in gradients
          lkernel.updateParameters(gradients[node],gain,self.stepSize)

    rhoWeight = regenAndAttach(trace,scaffold.border[0],scaffold,True,self.rhoDB,{})
    detachAndExtract(trace,scaffold.border[0],scaffold)
    assertTorus(scaffold)

    xiWeight = regenAndAttach(trace,scaffold.border[0],scaffold,False,OmegaDB(),{})
    return xiWeight - rhoWeight

  def accept(self): 
    if self.delegate is None:
      pass
    else:
      self.delegate.accept()

  def reject(self):
    if self.delegate is None:
      detachAndExtract(self.trace,self.scaffold.border[0],self.scaffold)
      assertTorus(self.scaffold)
      regenAndAttach(self.trace,self.scaffold.border[0],self.scaffold,True,self.rhoDB,{})
    else:
      self.delegate.reject()

################## PGibbs

# Construct ancestor path backwards
def constructAncestorPath(ancestorIndices,t,n):
  if t > 0: path = [ancestorIndices[t][n]]
  else: path = []

  for i in reversed(range(1,t)): path.insert(0, ancestorIndices[i][path[0]])
  assert len(path) == t
  return path

# Restore the particle along the ancestor path
def restoreAncestorPath(trace,border,scaffold,omegaDBs,t,path):
  for i in range(t):
    selectedDB = omegaDBs[i][path[i]]
    regenAndAttach(trace,border[i],scaffold,True,selectedDB,{})

# detach the rest of the particle
def detachRest(trace,border,scaffold,t):
  for i in reversed(range(t)): 
    detachAndExtract(trace,border[i],scaffold)


# P particles, not including RHO
# T groups of sinks, with T-1 resampling steps
# and then one final resampling step to select XI
class PGibbsOperator(object):
  def __init__(self,P):
    self.P = P

  def propose(self,trace,scaffold):
    self.trace = trace
    self.scaffold = scaffold

    ### TODO TEMPORARY
    assertTrace(self.trace,self.scaffold)

    self.T = 1

    T = self.T
    P = self.P
    ### END INSANITY

    rhoWeights = [None for t in range(T)]
    omegaDBs = [[None for p in range(P+1)] for t in range(T)]
    ancestorIndices = [[None for p in range(P)] + [P] for t in range(T)]

    self.omegaDBs = omegaDBs
    self.ancestorIndices = ancestorIndices

    for t in reversed(range(T)):
      (rhoWeights[t],omegaDBs[t][P]) = detachAndExtract(trace,scaffold.border[t],scaffold)

    assertTorus(scaffold)
    xiWeights = [None for p in range(P)]

    # Simulate and calculate initial xiWeights
    for p in range(P):
      regenAndAttach(trace,scaffold.border[0],scaffold,False,OmegaDB(),{})
      (xiWeights[p],omegaDBs[0][p]) = detachAndExtract(trace,scaffold.border[0],scaffold)

#    for every time step,
    for t in range(1,T):
      newWeights = [None for p in range(P)]
      # Sample new particle and propagate
      for p in range(P):
        extendedWeights = xiWeights + [rhoWeights[t-1]]
        ancestorIndices[t][p] = sampleCategorical([math.exp(w) for w in extendedWeights])
        path = constructAncestorPath(ancestorIndices,t,n)
        restoreAncestorPath(trace,self.scaffold.border,self.scaffold,omegaDBs,t,path)
        regenAndAttach(trace,self.scaffold.border[t],self.scaffold,False,OmegaDB(),{})
        (newWeights[p],omegaDBs[t][p]) = detachAndExtract(trace,self.scaffold.border[t],self.scaffold)
        detachRest(trace,self.scaffold.border,self.scaffold,t)
      xiWeights = newWeights

    # Now sample a NEW particle in proportion to its weight
    finalIndex = sampleCategorical([math.exp(w) for w in xiWeights])
#    assert finalIndex == 0
    rhoWeight = rhoWeights[T-1]
    xiWeight = xiWeights[finalIndex]

    weightMinusXi = math.log(sum([math.exp(w) for w in xiWeights]) + math.exp(rhoWeight) - math.exp(xiWeight))
    weightMinusRho = math.log(sum([math.exp(w) for w in xiWeights]))

#    assert weightMinusXi == rhoWeight
#    assert weightMinusRho == xiWeight

    path = constructAncestorPath(ancestorIndices,T-1,finalIndex) + [finalIndex]
    assert len(path) == T
#    assert path == [0]
    restoreAncestorPath(trace,self.scaffold.border,self.scaffold,omegaDBs,T,path)
    assertTrace(self.trace,self.scaffold)
    alpha = weightMinusRho - weightMinusXi
#    print "alpha: ",alpha
    return alpha

  def accept(self):
#    print "."
    pass
  def reject(self):
#    print "!"
    detachRest(self.trace,self.scaffold.border,self.scaffold,self.T)
    assertTorus(self.scaffold)
    path = constructAncestorPath(self.ancestorIndices,self.T-1,self.P) + [self.P]
    assert path == [self.P]
    assert len(path) == self.T
    restoreAncestorPath(self.trace,self.scaffold.border,self.scaffold,self.omegaDBs,self.T,path)
    assertTrace(self.trace,self.scaffold)
