from venture.lite.env import VentureEnvironment
from venture.lite.exception import VentureError

from venture.mite.sp import VentureSP
from venture.mite.sp import ApplicationKernel

from venture.mite.util import log_regen_event_at

class CompoundSP(VentureSP):
  def __init__(self, params, exp, env):
    super(CompoundSP, self).__init__()
    self.params = params
    self.exp = exp
    self.env = env

  def apply(self, trace_handle, application_id, inputs):
    if len(self.params) != len(inputs):
      raise VentureError("Wrong number of arguments: " \
        "compound with body %s takes exactly %d arguments, got %d." \
        % (self.exp, len(self.params), len(inputs)))
    extendedEnv = VentureEnvironment(self.env, self.params, inputs)
    addr = trace_handle.request_address(application_id)
    result = trace_handle.eval_request(
      addr, self.exp, extendedEnv)
    return result

  def unapply(self, trace_handle, application_id, _output, _inputs):
    log_regen_event_at("Unapplying compound application at", trace_handle.trace, application_id)
    addr = trace_handle.request_address(application_id)
    trace_handle.uneval_request(addr)
    return None

  def restore(self, trace_handle, application_id, _inputs, _frag):
    addr = trace_handle.request_address(application_id)
    result = trace_handle.restore_request(addr)
    return result

  def propagating_kernel(self, trace_handle, application_id, parent):
    addr = trace_handle.request_address(application_id)
    if addr == parent:
      # print "Choosing to propagate to", application_id, "from", parent
      return RequestPropagatingKernel(trace_handle, addr)
    else:
      return None

  def request_constraint_kernel(self, trace_handle, application_id):
    # TODO Should this accept the identity of the request made, or
    # should we assume the SP can deduce it?
    addr = trace_handle.request_address(application_id)
    return RequesterConstraintKernel(trace_handle, addr)

class RequestPropagatingKernel(ApplicationKernel):
  def __init__(self, trace_handle, request_addr):
    self.trace_handle = trace_handle
    self.request_addr = request_addr

  def extract(self, output, _inputs):
    return (0, output)

  def regen(self, _inputs):
    output = self.trace_handle.value_at(self.request_addr)
    return (0, output)

  def restore(self, _inputs, output):
    return output

class RequesterConstraintKernel(ApplicationKernel):
  def __init__(self, trace_handle, request_addr):
    self.trace_handle = trace_handle
    self.request_addr = request_addr
    self.saved_output = None

  def extract(self, output, _inputs):
    # In this case, the output of the whole application.
    self.saved_output = output
    return (0, output)

  def regen(self, _inputs):
    # Sadly, if this is the only kernel, its regen method is
    # responsible for the result of the whole application.  If it is
    # indeed the only kernel, then the output must not have changed,
    # so we should be able to return the old one.
    return (0, self.saved_output)

  def restore(self, _inputs, output):
    return output
