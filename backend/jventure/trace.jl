require("node.jl")
require("eearray.jl")
require("builtins.jl")
require("db.jl")

typealias DirectiveID Int

type Trace
  rcs::EEArray{Node}
  aes::Set{Node}
  families::Dict{DirectiveID,Node}
  esrParents::Dict{Node,Array{Node}}
  madeSPRecords::Dict{Node,SPRecord}
  children::Dict{Node,Set{Node}}
  observedValues::Dict{Node,Any}
  constrainedNodes::Set{Node}
  globalEnv::ExtendedEnvironment
end

function Trace()
  trace = Trace(EEArray{Node}((Node=>Int)[],Array(Node,0)),
                Set{Node}(),
                (DirectiveID=>Node)[],
                (Node=>Array{Node})[],
                (Node=>SPRecord)[],
                (Node=>Set{Node})[],
                (Node=>Any)[],
                Set{Node}(),
                ExtendedEnvironment((Symbol=>Node)[],EmptyEnvironment()))

  for (name,sp) = builtInSPs
    spNode = createConstantNode(trace,sp)
    processMadeSP(trace,spNode,false)
    @assert isa(getValue(trace,spNode),SPRef)
    addBinding!(trace.globalEnv,name,spNode)
  end

  return trace
end

## Creating nodes  
function createConstantNode(trace::Trace,value::Any)
  constantNode = ConstantNode(value)
  trace.children[constantNode] = Set{Node}()
  return constantNode
end

function createLookupNode(trace::Trace,sourceNode::Node)
  lookupNode = LookupNode(sourceNode)
  push!(trace.children[sourceNode],lookupNode)
  trace.children[lookupNode] = Set{Node}()
  return lookupNode
end

function createApplicationNodes(trace::Trace,operatorNode::Node,operandNodes::Array{Node},env::ExtendedEnvironment)
  requestNode = RequestNode(operatorNode,operandNodes,env)
  outputNode = OutputNode(requestNode)
  push!(trace.children[operatorNode],requestNode)
  for operandNode = operandNodes
    push!(trace.children[operandNode],requestNode)
  end
  trace.children[requestNode] = Set{Node}(outputNode)
  trace.children[outputNode] = Set{Node}()
  trace.esrParents[outputNode] = Array(Node,0)
  return (requestNode,outputNode)
end

reconnectLookup!(trace::Trace,node::LookupNode) = push!(trace.children[node.sourceNode],node)
disconnectLookup!(trace::Trace,node::LookupNode) = delete!(trace.children[node.sourceNode],node)

## Random Choices
registerRandomChoice!(trace::Trace,node::ApplicationNode) = push!(trace.rcs,node)
unregisterRandomChoice!(trace::Trace,node::ApplicationNode) = delete!(trace.rcs,node)

registerAEKernel!(trace::Trace,node::OutputNode) = push!(trace.aes,node)
unregisterAEKernel!(trace::Trace,node::OutputNode) = delete!(trace.aes,node)

### ESR Edges
function registerESREdge!(trace::Trace,esrParent::Node,outputNode::OutputNode)
  push!(trace.esrParents[outputNode],esrParent)
  @assert !isempty(trace.esrParents[outputNode])
  push!(trace.children[esrParent],outputNode)
  esrParent.numRequests += 1  

end

function popLastESRParent!(trace::Trace,outputNode::OutputNode)
  @assert !isempty(trace.esrParents[outputNode])
  esrParent = pop!(trace.esrParents[outputNode])
  delete!(trace.children[esrParent],outputNode)
  esrParent.numRequests -= 1
  return esrParent
end

############## Getters

### Parents
getParents(trace::Trace,node::ConstantNode) = (Node)[]
getParents(trace::Trace,node::LookupNode) = (Node)[node.sourceNode]
getParents(trace::Trace,node::RequestNode) = vcat((Node)[node.operatorNode],node.operandNodes)
getParents(trace::Trace,node::OutputNode) = vcat(getParents(trace,node.requestNode),(Node)[node.requestNode],getESRParents(trace,node))

getOperatorNode(trace::Trace,node::RequestNode) = node.operatorNode
getOperatorNode(trace::Trace,node::OutputNode) = node.requestNode.operatorNode

getOperandNodes(trace::Trace,node::RequestNode) = node.operandNodes
getOperandNodes(trace::Trace,node::OutputNode) = node.requestNode.operandNodes

### Children
getChildren(trace::Trace,node::Node) = trace.children[node] # Warning: doesn't include operat(or/and)=>output
getNumberOfChildren(trace::Trace,node::Node) = length(trace.children[node]) + length(filter(x->isa(x,RequestNode),trace.children[node]))

function getOutputNode(trace::Trace,node::RequestNode)
  children = [x for x in trace.children[node]]
  @assert length(children) == 1
  return children[1]
end

getNumberOfRequests(trace::Trace,node::Node) = node.numRequests

### SPs
function getGroundValue(trace::Trace,node::ApplicationNode)
  value = getValue(trace,node)
  if isa(value,SPRef)
    return getMadeSP(trace,value.makerNode)
  else
    return value
  end
end

function getSPRef(trace::Trace,node::ApplicationNode)
  spref = getValue(trace,getOperatorNode(trace,node))
  @assert isa(spref,SPRef)
  return spref
end

function getSPRecord(trace::Trace,node::ApplicationNode) 
  @assert haskey(trace.madeSPRecords,getSPRef(trace,node).makerNode)
  return trace.madeSPRecords[getSPRef(trace,node).makerNode]
end

getSP(trace::Trace,node::ApplicationNode) = getSPRecord(trace,node).sp
getSPAux(trace::Trace,node::ApplicationNode) = getSPRecord(trace,node).aux
getSPFamilies(trace::Trace,node::ApplicationNode) = getSPRecord(trace,node).families

getPSP(trace::Trace,node::RequestNode) = getSP(trace,node).requestPSP
getPSP(trace::Trace,node::OutputNode) = getSP(trace,node).outputPSP

function createMadeSPRecord!(trace::Trace,node::Union(ConstantNode,OutputNode),sp::SP,spaux::Any)
  trace.madeSPRecords[node] = SPRecord(sp,spaux,Dict{SPFamilyID,Node}())
end

function destroyMadeSPRecord!(trace::Trace,node::Union(ConstantNode,OutputNode))
  delete!(trace.madeSPRecords,node)
end

function setMadeSP!(trace::Trace,node::OutputNode,sp::Union(SP,Nothing))
  @assert haskey(trace.madeSPRecords,node)
  trace.madeSPRecords[node].sp = sp
end

function getMadeSPRecord(trace::Trace,node::OutputNode)
  if haskey(trace.madeSPRecords,node)
    return trace.madeSPRecords[node]
  else
    return nothing
  end
end

getMadeSP(trace::Trace,node::Union(ConstantNode,OutputNode)) = getMadeSPRecord(trace,node).sp

### Values
function getValue(trace::Trace,node::Node)
  @assert node.value != nothing
  return node.value
end

function setValue!(trace::Trace,node::Node,value::Any)
  node.value = value
end

isObservation(trace::Trace,node::Node) = haskey(trace.observedValues,node)
getObservedValue(trace::Trace,node::Node) = trace.observedValues[node]
isConstrained(trace::Trace,node::Node) = in(node,trace.constrainedNodes)

function setConstrained!(trace::Trace,node::Node)
  @assert !in(node,trace.constrainedNodes)
  push!(trace.constrainedNodes,node)
end

function setUnconstrained!(trace::Trace,node::Node)
  @assert in(node,trace.constrainedNodes)
  delete!(trace.constrainedNodes,node)
end

### EsrParents
getESRParents(trace::Trace,node::OutputNode) = trace.esrParents[node]
function getESRSourceNode(trace::Trace,node::OutputNode)
  @assert length(trace.esrParents[node]) == 1
  return trace.esrParents[node][1]
end

### Args
function getArgs(trace::Trace,node::RequestNode)
  return RequestArgs(node,[n.value for n = node.operandNodes],node.operandNodes,getSPAux(trace,node),node.env)
end

function getArgs(trace::Trace,node::OutputNode)
  operandValues = [n.value for n = getOperandNodes(trace,node)]
  operandNodes = getOperandNodes(trace,node)

  requestValue = node.requestNode.value
  esrParentValues = [n.value for n = getESRParents(trace,node)]
  esrParentNodes = getESRParents(trace,node)

  # TODO should be a maybeSPAux
  madeSPAux = haskey(trace.madeSPRecords,node) ? getMadeSPRecord(trace,node).aux : nothing
  spaux::Any = getSPAux(trace,node)
  env::ExtendedEnvironment = node.env
  
  return OutputArgs(node,operandValues,operandNodes,requestValue,esrParentValues,esrParentNodes,madeSPAux,spaux,env)
end

### Engine-facing
require("scaffold.jl")
require("regen.jl")

function evalExpression(trace::Trace,id::DirectiveID,exp::Any)
  @assert !haskey(trace.families,id)
  (_,trace.families[id]) = evalFamily(trace,exp,trace.globalEnv,Scaffold(),DB())
end

function bindInGlobalEnv(trace::Trace,sym::Symbol,id::DirectiveID)
  addBinding!(trace.globalEnv,sym,trace.families[id])
end

extractValue(trace::Trace,id::DirectiveID) = trace.families[id].value

function observe(trace::Trace,id::DirectiveID,value::Any)
  node = trace.families[id]
  trace.observedValues[node] = value
  return constrain(trace,node,value)
end

### Kernel facing
logDensityOfPrincipalNode(trace::Trace,pnode::Node) = -log(length(trace.rcs))
samplePrincipalNode(trace::Trace) = sample(trace.rcs)

require("lkernel.jl")
require("infer.jl")

function infer(trace::Trace,N::Int)
  for i = 1:N
    mhInfer(trace,samplePrincipalNode(trace))
  end
end

function showScaffoldSize(s::Scaffold)
  print((length(s.regenCounts),length(s.absorbing),length(s.aaa)))
end

function showScaffoldSizes(trace::Trace)
  println("---")
  for node = trace.rcs.v
    s = constructScaffold(trace,Set{Node}(node))
    showScaffoldSize(s)
    println(" ")
  end
  println("---")
end

function loggingInfer(trace::Trace,id::DirectiveID,N::Int)
  predictions = Array(Any,N)
  for n = 1:N
    mhInfer(trace,samplePrincipalNode(trace))
    if n % 5 == 0 # TODO Hard-coded Constant
      for node = trace.aes # can all be in parallel
        AEInfer(getMadeSP(trace,node).outputPSP,getArgs(trace,node))
      end
    end
    predictions[n] = extractValue(trace,id)
  end
  return predictions
end
