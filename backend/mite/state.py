import venture.lite.types as t

from venture.mite.sp import VentureSP, SimulationSP
from venture.mite.sp_registry import registerBuiltinSP


def register_subtrace_type(name, cls, actions):
  constructor = SubtraceConstructorSP(cls)
  registerBuiltinSP(name, constructor)
  for action_name, action_sp in actions.iteritems():
    action_func_name = action_name + "_func"
    registerBuiltinSP(action_func_name, action_sp)
    (params, body) = action_sp.action_defn(action_func_name)
    body = t.Exp.asPython(t.Exp.asVentureValue(body))
    registerBuiltinSP(action_name, (params, body))


class SubtraceConstructorSP(SimulationSP):
  def __init__(self, trace_class):
    self.trace_class = trace_class

  def simulate(self, inputs, _prng):
    assert len(inputs) == 0
    return t.Blob.asVentureValue(self.trace_class())


class SubtracePropertySP(SimulationSP):
  def __init__(self, property_name, property_type):
    self.name = property_name
    self.output_type = property_type

  def simulate(self, inputs, _prng):
    assert len(inputs) == 1
    trace = t.Blob.asPython(inputs[0])
    output = getattr(trace, self.name)
    return t.Pair(self.output_type, t.Blob).asVentureValue(
      (output, trace))

  def action_defn(self, action_func_name):
    # interpreted by register_subtrace_type
    return ([], ['inference_action', action_func_name])

subtrace_property = SubtracePropertySP


# TODO: this should have an unapply method that undoes its effect on
# the trace.
class SubtraceActionSP(SimulationSP):
  def __init__(self, method_name, input_types, output_type):
    self.name = method_name
    self.input_types = input_types
    self.output_type = output_type

  def simulate(self, inputs, _prng):
    assert len(inputs) == 1 + len(self.input_types)
    trace = t.Blob.asPython(inputs[0])
    inputs = [in_t.asPython(value) for in_t, value in
              zip(self.input_types, inputs[1:])]
    output = getattr(trace, self.name)(*inputs)
    return t.Pair(self.output_type, t.Blob).asVentureValue(
      (output, trace))

  def action_defn(self, action_func_name):
    # interpreted by register_subtrace_type
    names = ['var{}'.format(i) for i in range(len(self.input_types))]
    return (names,
            ['inference_action',
             ['make_csp', ['quote', ['trace']],
              ['quote', [action_func_name, 'trace'] + names]]])

subtrace_action = SubtraceActionSP
