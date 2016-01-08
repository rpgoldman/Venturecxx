# Copyright (c) 2015 MIT Probabilistic Computing Project.
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

import os.path
from venture.test.config import get_ripl
import venture.test.errors as err

plugin_name = "plugin.py"
this_dir = os.path.dirname(os.path.abspath(__file__))
plugin_abs_path = os.path.join(this_dir, plugin_name)

def testPluginsLoad():
  r = get_ripl()
  r.load_plugin(plugin_abs_path)
  r.infer("(call_back foo)")

def testPluginsLoad2():
  r = get_ripl()
  r.infer("(load_plugin (quote symbol<\"" + plugin_abs_path + "\">))")
  r.infer("(call_back foo)")

def testPluginsLoad3():
  r = get_ripl()
  r.infer("""(do
  (seven <- (load_plugin (quote symbol<"%s">)))
  (assert (eq 7 seven)))""" % (plugin_abs_path,))

def testPluginsLoad4():
  r = get_ripl(extra_search_paths = [this_dir])
  r.infer("""(do
  (seven <- (load_plugin (quote symbol<"%s">)))
  (assert (eq 7 seven)))""" % (plugin_name,))

def testPluginsLoadFail():
  r = get_ripl(extra_search_paths = [this_dir])
  err.assert_error_message_contains("Plugin frob.py not found in any of ['/home/axch/work/pcp/Venturecxx/test/integration', '/home/axch/work/pcp/Venturecxx/build/lib.linux-x86_64-2.7/venture/plugins', '.']",
  r.infer, '(load_plugin "frob.py")')
