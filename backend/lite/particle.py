from copy import copy
import math

from trace import Trace

class Particle(Trace):
  # The trace is expected to be a torus, with the chosen scaffold
  # already detached.
  def __init__(self,trace):
    self.base = trace
    self.cache = {} # TODO persistent map from nodes to node records
    self.rcs = [] # TODO persistent set?

  def _at(self,node):
    if node in self.cache:
      return self.cache[node]
    else:
      return record_for(node)

  def _alterAt(self,node,f):
    # self.cache = self.cache.insert(node,f(self._at(node)))
    self.cache[node] = f(self._at(node))

  def _alterSpauxAt(self,node,f):
    self._alterAt(self.spRefAt(node).makerNode, lambda r: r.update(madeSPAux=f(r.madeSPAux)))

  def valueAt(self,node):
    return self._at(node).value
  def setValueAt(self,node,value):
    self._alterAt(node, lambda r: r.update(value=value))
  def madeSPAt(self,node):
    return self._at(node).madeSP
  def setMadeSPAt(self,node,sp):
    self._alterAt(node, lambda r: r.update(madeSP=sp))
  def madeSPAuxAt(self,node):
    return self._at(node).madeSPAux
  def setMadeSPAuxAt(self,node,aux):
    self._alterAt(node, lambda r: r.update(madeSPAux=aux))
  def esrParentsAt(self,node):
    return self._at(node).esrParents
  def appendEsrParentAt(self,node,parent):
    self._alterAt(node, lambda r: r.append_esrParent(parent))
  def popEsrParentAt(self,node):
    ans = self._at(node).top_esrParent()
    self._alterAt(node, lambda r: r.pop_esrParent())
    return ans
  def childrenAt(self,node):
    return self._at(node).children
  def addChildAt(self,node,child):
    self._alterAt(node, lambda r: r.add_child(child))
  def removeChildAt(self,node,child):
    self._alterAt(node, lambda r: r.remove_child(child))
  def registerFamilyAt(self,node,esrId,esrParent):
    self._alterSpauxAt(node, lambda spauxr: spauxr.registerFamily(esrId,esrParent))
  def unregisterFamilyAt(self,node,esrId):
    self._alterSpauxAt(node, lambda spauxr: spauxr.unregisterFamily(esrId))
  def numRequestsAt(self,node):
    return self._at(node).numRequests
  def incRequestsAt(self,node):
    self._alterAt(node, lambda r: r.update(numRequests = r.numRequests + 1))
  def decRequestsAt(self,node):
    self._alterAt(node, lambda r: r.update(numRequests = r.numRequests - 1))

  def registerRandomChoice(self,node):
    assert not node in self.rcs
    self.rcs.append(node)

  def unregisterRandomChoice(self,node):
    assert node in self.rcs
    del self.rcs[self.rcs.index(node)]

  def logDensityOfPrincipalNode(self,node):
    ct = len(self.base.rcs) + len(self.rcs)
    return -1 * math.log(ct)

  def commit(self):
    for (node,r) in self.cache.iteritems():
      r.commit(self.base, node)
    self.base.rcs = self.base.rcs + self.rcs

def record_for(node):
  return Record(value=node.Tvalue, madeSP=node.TmadeSP, madeSPAux=spaux_record_for(node.TmadeSPAux),
                esrParents=node.TesrParents, children=node.Tchildren, numRequests=node.TnumRequests)

class Record(object):
  def __init__(self,value=None,madeSP=None,madeSPAux=None,esrParents=None,children=None,numRequests=0):
    self.value = value
    self.madeSP = madeSP
    self.madeSPAux = madeSPAux
    self.esrParents = []
    if esrParents: self.esrParents = esrParents
    self.children = set()
    if children: self.children = children
    self.numRequests = numRequests

  def _copy(self):
    return Record(self.value, self.madeSP, self.madeSPAux, self.esrParents, self.children, self.numRequests)

  def update(self,value=None,madeSP=None,madeSPAux=None,esrParents=None,children=None,numRequests=None):
    ans = self._copy()
    if value: ans.value = value
    if madeSP: ans.madeSP = madeSP
    if madeSPAux: ans.madeSPAux = madeSPAux
    if esrParents: ans.esrParents = esrParents
    if children: ans.children = children
    if numRequests: ans.numRequests = numRequests
    return ans

  def add_child(self,child):
    new_children = copy(self.children)
    new_children.add(child)
    return self.update(children=new_children)

  def remove_child(self,child):
    new_children = copy(self.children)
    new_children.remove(child)
    return self.update(children=new_children)

  def top_esrParent(self):
    return self.esrParents[len(self.esrParents)-1]

  def pop_esrParent(self):
    new_esrParents = [p for p in self.esrParents]
    new_esrParents.pop()
    return self.update(esrParents=new_esrParents)

  def append_esrParent(self,parent):
    new_esrParents = [p for p in self.esrParents]
    new_esrParents.append(parent)
    return self.update(esrParents=new_esrParents)

  def commit(self,trace,node):
    if self.value: trace.setValueAt(node,self.value)
    if self.madeSP: trace.setMadeSPAt(node,self.madeSP)
    if self.madeSPAux: self.madeSPAux.commit(trace,node)
    if self.esrParents: trace.setEsrParentsAt(node,self.esrParents)
    if self.children: trace.setChildrenAt(node,self.children)
    if self.numRequests: trace.setNumRequestsAt(node,self.numRequests)

def spaux_record_for(spaux):
  if spaux == None:
    return None
  return SPAuxRecord(copy(spaux.families))

class SPAuxRecord(object):
  def __init__(self,families={}): # id => node TODO persistent
    self.families = families
  def containsFamily(self,id): return id in self.families
  def getFamily(self,id): return self.families[id]
  def registerFamily(self,id,esrParent):
    assert not id in self.families
    new_families = copy(self.families)
    new_families[id] = esrParent
    return SPAuxRecord(new_families)
  def unregisterFamily(self,id):
    new_families = copy(self.families)
    new_families.delete(id)
    return SPAuxRecord(new_families)

  def commit(self,trace,node):
    for (id,esrParent) in self.families.iteritems():
      trace.madeSPAuxAt(node).registerFamily(id,esrParent) # TODO Go through the trace for the actual registration?
