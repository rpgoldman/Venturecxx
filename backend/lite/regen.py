from exp import isVariable, isSelfEvaluating, isQuotation, textOfQuotation, getOperator, getOperands
from node import ConstantNode, LookupNode, ApplicationNode, RequestNode, OutputNode
from sp import SP
from psp import ESRRefOutputPSP
from spref import SPRef
from lkernel import VariationalLKernel

def regenAndAttach(trace,border,scaffold,shouldRestore,omegaDB,gradients):
  weight = 0
  for node in border:
    if scaffold.isAbsorbing(node):
      weight += attach(trace,node,scaffold,shouldRestore,omegaDB,gradients)
    else:
      weight += regen(trace,node,scaffold,shouldRestore,omegaDB,gradients)
      if node.isObservation: weight += constrain(trace,node,node.observedValue)
  return weight

def constrain(trace,node,value):
  if isinstance(node,LookupNode): return constrain(trace,node.sourceNode,value)
  assert isinstance(node,OutputNode)
  if isinstance(trace.pspAt(node),ESRRefOutputPSP): return constrain(trace,trace.esrParentsAt(node)[0],value)
  trace.unincorporateAt(node)
  weight = trace.logDensityAt(node,value)
  trace.setValueAt(node,value)
  trace.incorporateAt(node)
  trace.unregisterRandomChoice(node)
  return weight

def attach(trace,node,scaffold,shouldRestore,omegaDB,gradients):
  weight = regenParents(trace,node,scaffold,shouldRestore,omegaDB,gradients)
  weight += trace.logDensityAt(node,trace.groundValueAt(node))
  trace.incorporateAt(node)
  return weight

def regenParents(trace,node,scaffold,shouldRestore,omegaDB,gradients):
  weight = 0
  for parent in trace.parentsAt(node): weight += regen(trace,parent,scaffold,shouldRestore,omegaDB,gradients)
  return weight

def regen(trace,node,scaffold,shouldRestore,omegaDB,gradients):
  weight = 0
  if scaffold.isResampling(node):
    if scaffold.regenCount(node) == 0:
      weight += regenParents(trace,node,scaffold,shouldRestore,omegaDB,gradients)
      if isinstance(node,LookupNode):
        trace.setValueAt(node, trace.valueAt(node.sourceNode))
      else: 
        weight += applyPSP(trace,node,scaffold,shouldRestore,omegaDB,gradients)
        if isinstance(node,RequestNode): weight += evalRequests(trace,node,scaffold,shouldRestore,omegaDB,gradients)
    scaffold.incrementRegenCount(node)

  value = trace.valueAt(node)
  if isinstance(value,SPRef) and value.makerNode != node and scaffold.isAAA(value.makerNode):
    weight += regen(trace,value.makerNode,scaffold,shouldRestore,omegaDB,gradients)

  return weight

def evalFamily(trace,exp,env,scaffold,omegaDB,gradients):
  weight = 0
  if isVariable(exp): 
    sourceNode = env.findSymbol(exp)
    regen(trace,sourceNode,scaffold,False,omegaDB,gradients)
    return (0,trace.createLookupNode(sourceNode))
  elif isSelfEvaluating(exp): return (0,trace.createConstantNode(exp))
  elif isQuotation(exp): return (0,trace.createConstantNode(textOfQuotation(exp)))
  else:
    (weight,operatorNode) = evalFamily(trace,getOperator(exp),env,scaffold,omegaDB,gradients)
    operandNodes = []
    for operand in getOperands(exp):
      (w,operandNode) = evalFamily(trace,operand,env,scaffold,omegaDB,gradients)
      weight += w
      operandNodes.append(operandNode)

    (requestNode,outputNode) = trace.createApplicationNodes(operatorNode,operandNodes,env)
    requestNode.scopes = expScopes(exp)
    outputNode.scopes = expScopes(exp)
    weight += apply(trace,requestNode,outputNode,scaffold,False,omegaDB,gradients)
    return weight,outputNode

def apply(trace,requestNode,outputNode,scaffold,shouldRestore,omegaDB,gradients):
  weight = applyPSP(trace,requestNode,scaffold,shouldRestore,omegaDB,gradients)
  weight += evalRequests(trace,requestNode,scaffold,shouldRestore,omegaDB,gradients)
  weight += applyPSP(trace,outputNode,scaffold,shouldRestore,omegaDB,gradients)
  return weight

def processMadeSP(trace,node,isAAA):
  sp = trace.valueAt(node)
  assert isinstance(sp,SP)
  trace.setMadeSPAt(node,sp)
  trace.setValueAt(node,SPRef(node))
  if not isAAA:
    trace.setMadeSPAux(node, sp.constructSPAux())
    if sp.hasAEKernel(): trace.registerAEKernel(node)

def applyPSP(trace,node,scaffold,shouldRestore,omegaDB,gradients):
  weight = 0;

  if omegaDB.hasValueFor(node): oldValue = omegaDB.getValue(node)
  else: oldValue = None

  if shouldRestore: newValue = oldValue
  elif scaffold.hasKernelFor(node):
    k = scaffold.getKernel(node)
    newValue = k.simulate(trace,oldValue,trace.argsAt(node))
    weight += k.weight(trace,newValue,oldValue,trace.argsAt(node))
    if isinstance(k,VariationalLKernel): 
      gradients[node] = k.gradientOfLogDensity(newValue,trace.argsAt(node))
  else: 
    # if we simulate from the prior, the weight is 0
    newValue = trace.pspAt(node).simulate(trace.argsAt(node))

  trace.setValueAt(node,newValue)
  trace.incorporateAt(node)

  if isinstance(newValue,SP): processMadeSP(trace,node,scaffold.isAAA(node))
  if trace.pspAt(node).isRandom(): trace.registerRandomChoice(node)
  return weight

def evalRequests(trace,node,scaffold,shouldRestore,omegaDB,gradients):
  assert isinstance(node,RequestNode)
  weight = 0;
  request = trace.valueAt(node)

  # first evaluate exposed simulation requests (ESRs)
  for esr in request.esrs:
    if not trace.spauxAt(node).containsFamily(esr.id):
      if shouldRestore: 
        esrParent = omegaDB.getESRParent(trace.spAt(node),esr.id)
        weight += restore(trace,esrParent,scaffold,omegaDB,gradients)
      else:
        (w,esrParent) = evalFamily(trace,esr.exp,esr.env,scaffold,omegaDB,gradients)
        weight += w
      trace.registerFamilyAt(node,esr.id,esrParent)
    else:
      esrParent = trace.spauxAt(node).getFamily(esr.id)
      weight += regen(trace,esrParent,scaffold,shouldRestore,omegaDB,gradients)
    esrParent = trace.spauxAt(node).getFamily(esr.id)
    if esr.block: trace.registerBlock(esr.block,esr.subblock,esrParent)
    trace.addESREdge(esrParent,node.outputNode)

  # next evaluate latent simulation requests (LSRs)
  for lsr in request.lsrs:
    if omegaDB.hasLatentDB(trace.spAt(node)): latentDB = omegaDB.getLatentDB(trace.apAt(node))
    else: latentDB = None
    weight += trace.spAt(node).simulateLatents(trace.spauxAt(node),lsr,shouldRestore,latentDB)
  
  return weight;

def restore(trace,node,scaffold,omegaDB,gradients):
  if isinstance(node,ConstantNode): return 0
  if isinstance(node,LookupNode):
    weight = regen(trace,node.sourceNode,scaffold,True,omegaDB,gradients)
    trace.setValueAt(node,trace.valueAt(node.sourceNode))
    trace.reconnectLookup(node)
    return weight
  else: # node is output node
    weight = restore(trace,node.operatorNode,scaffold,omegaDB,gradients)
    for operandNode in node.operandNodes: weight += restore(trace,operandNode,scaffold,omegaDB,gradients)
    weight += apply(trace,node.requestNode,node,scaffold,True,omegaDB,gradients)
    return weight
