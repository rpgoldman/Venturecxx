from graphviz import Digraph

from venture.lite.orderedset import OrderedSet

import venture.mite.address as addr
from venture.mite.render import _jsonable_address

def digraph(trace, scaffold, principal_nodes=None):
  if principal_nodes is None:
    principal_nodes = set()
  dot = Digraph(name="A scaffold")
  for ad in scaffold.kernels.keys():
    name = _node_name(ad)
    ker = scaffold.kernels[ad]
    if ad in principal_nodes:
      color = 'red'
    elif kernel_type(ker) == 'proposal' or kernel_type(ker) == 'propagate_lookup':
      color = 'yellow'
    elif kernel_type(ker) == 'constrained':
      color = 'blue'
    dot.node(name, label=name, fillcolor=color, style="filled")
  brush = _compute_brush_hack(trace, scaffold)
  for ad in brush:
    name = _node_name(ad)
    dot.node(name, label=name, fillcolor='green', style="filled")
  _add_links(dot, trace, scaffold.kernels.keys() + list(brush))
  return dot

def kernel_type(ker):
  if isinstance(ker, dict) and 'type' in ker:
    return ker['type']
  else:
    return None

def digraph_trace(trace):
  dot = Digraph(name="A trace")
  addrs = [ad for ad in trace.nodes.keys() if not isinstance(ad, addr.BuiltinAddress)]
  for ad in addrs:
    name = _node_name(ad)
    dot.node(name, label=name)
  _add_links(dot, trace, addrs)
  return dot

def _add_links(dot, trace, addrs):
  for ad in addrs:
    # Hack in dependencies due to requests created by compound SPs
    if isinstance(ad, addr.RequestAddress):
      extra_children = [ad.request_id]
    else:
      extra_children = []
    for child in list(trace.nodes[ad].children) + extra_children:
      if child in addrs:
        dot.edge(_node_name(ad), _node_name(child))

def _node_name(ad):
  return _jsonable_address(ad)

def _compute_brush_hack(trace, scaffold):
  # If the only requesting SPs are CompoundSP, then
  # - All requests whose ids are addresses of nodes whose operators
  #   are in the DRG or brush are brush
  # - All requests whose ids are addresses of nodes in the brush are
  #   brush
  # - All subexpressions whose sources are in the brush are brush
  # - All other nodes are not brush
  brush = OrderedSet([])
  def is_brush(ad):
    if isinstance(ad, addr.RequestAddress):
      if ad.request_id in brush:
        return True
      else:
        op_addr = addr.subexpression(0, ad.request_id)
        if op_addr in brush:
          return True
        elif op_addr in scaffold.kernels:
          ker = scaffold.kernels[op_addr]
          if kernel_type(ker) == 'proposal' or kernel_type(ker) == 'propagate_lookup':
            return True
        return False
    if isinstance(ad, addr.SubexpressionAddress):
      if ad.parent in brush: return True
    return False
  done = False
  while not done:
    done = True
    for ad in trace.nodes.keys():
      if ad in brush: continue
      if is_brush(ad):
        brush.add(ad)
        done = False
  return brush
