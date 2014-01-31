# Copyright (c) 2013, MIT Probabilistic Computing Project.
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
# You should have received a copy of the GNU General Public License along with Venture.  If not, see <http://www.gnu.org/licenses/>.
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from venture.exception import VentureException
from venture.sivm import utils
import copy


class VentureSivm(object):

    def __init__(self, core_sivm):
        self.core_sivm = core_sivm
        self._clear()
        self._init_continuous_inference()

    # list of all instructions supported by venture sivm
    _extra_instructions = {'labeled_assume','labeled_observe',
            'labeled_predict','labeled_forget','labeled_report', 'labeled_get_logscore',
            'list_directives','get_directive','labeled_get_directive',
            'force','sample','get_current_exception',
            'get_state', 'reset', 'debugger_list_breakpoints','debugger_get_breakpoint'}
    _core_instructions = {"assume","observe","predict",
            "configure","forget","report","infer","start_continuous_inference",
            "stop_continuous_inference","continuous_inference_status",
            "clear","rollback","get_directive_logscore","get_global_logscore",
            "debugger_configure","debugger_list_random_choices", "debugger_clear",
            "debugger_force_random_choice","debugger_report_address",
            "debugger_history","debugger_dependents","debugger_address_to_source_code_location",
            "debugger_set_breakpoint_address","debugger_set_breakpoint_source_code_location",
            "debugger_remove_breakpoint","debugger_continue","profiler_configure",
            "profiler_clear","profiler_list_random_choices",
            "profiler_address_to_source_code_location","profiler_get_random_choice_acceptance_rate",
            "profiler_get_global_acceptance_rate","profiler_get_random_choice_proposal_time",
            "profiler_get_global_proposal_time"}
    
    _dont_pause_continuous_inference = {"start_continuous_inference",
            "stop_continuous_inference", "continuous_inference_status"}
    
    def execute_instruction(self, instruction):
        utils.validate_instruction(instruction,self._core_instructions | self._extra_instructions)
        instruction_type = instruction['instruction']
        
        pause = instruction_type not in self._dont_pause_continuous_inference
        with self._pause_continuous_inference(pause=pause):
            if instruction_type in self._extra_instructions:
                f = getattr(self,'_do_'+instruction_type)
                return f(instruction)
            return self._call_core_sivm_instruction(instruction)

    ###############################
    # Reset stuffs
    ###############################

    def _clear(self):
        self.label_dict = {}
        self.did_dict = {}
        self.directive_dict = {}
        self._debugger_clear()
        self.state = 'default'

    def _debugger_clear(self):
        self.breakpoint_dict = {}

    ###############################
    # Sugars/desugars
    # for the CoreSivm instructions
    ###############################

    def _call_core_sivm_instruction(self,instruction):
        desugared_instruction = copy.deepcopy(instruction)
        instruction_type = instruction['instruction']
        # desugar the expression
        if instruction_type in ['assume','observe','predict']:
            exp = utils.validate_arg(instruction,'expression',
                    utils.validate_expression, wrap_exception=False)
            new_exp = utils.desugar_expression(exp)
            desugared_instruction['expression'] = new_exp
        # desugar the expression index
        if instruction_type == 'debugger_set_breakpoint_source_code_location':
            desugared_src_location = desugared_instruction['source_code_location']
            did = desugared_src_location['directive_id']
            old_index = desugared_src_location['expression_index']
            exp = self.directive_dict[did]['expression']
            new_index = utils.desugar_expression_index(exp, old_index)
            desugared_src_location['expression_index'] = new_index
        try:
            response = self.core_sivm.execute_instruction(desugared_instruction)
        except VentureException as e:
            if e.exception == "evaluation":
                self.state='exception'
                self.current_exception = e.to_json_object()
            if e.exception == "breakpoint":
                self.state='paused'
                self.current_exception = e.to_json_object()
            # re-sugar the expression index
            if e.exception == 'parse':
                i = e.data['expression_index']
                exp = instruction['expression']
                i = utils.sugar_expression_index(exp,i)
                e.data['expression_index'] = i
            # turn directive_id into label
            if e.exception == 'invalid_argument':
                if e.data['argument'] == 'directive_id':
                    did = e.data['directive_id']
                    if did in self.did_dict:
                        e.data['label'] = self.did_dict[did]
                        e.data['argument'] = 'label'
                        del e.data['directive_id']
            raise
        # clear the dicts on the "clear" command
        if instruction_type == 'clear':
            self._clear()
        # forget directive mappings on the "forget" command
        if instruction_type == 'forget':
            did = instruction['directive_id']
            del self.directive_dict[did]
            if did in self.did_dict:
                del self.label_dict[self.did_dict[did]]
                del self.did_dict[did]
        # save the directive if the instruction is a directive
        if instruction_type in ['assume','observe','predict']:
            did = response['directive_id']
            tmp_instruction = {}
            tmp_instruction['directive_id'] = did
            for key in ('instruction', 'expression', 'symbol', 'value'):
                if key in instruction:
                    tmp_instruction[key] = copy.deepcopy(instruction[key])
            self.directive_dict[did] = tmp_instruction
        # save the breakpoint if the instruction sets the breakpoint
        if instruction_type in ['debugger_set_breakpoint_address',
                'debugger_set_breakpoint_source_code_location']:
            bid = response['breakpoint_id']
            tmp_instruction = copy.deepcopy(instruction)
            tmp_instruction['breakpoint_id'] = bid
            del tmp_instruction['instruction']
            self.breakpoint_dict[bid] = tmp_instruction
        return response


    ###############################
    # Continuous Inference Pauser
    ###############################

    def _pause_continuous_inference(sivm, pause=True):
        class tmp(object):
            def __enter__(self):
                self.ci_status = sivm._continuous_inference_status()
                self.ci_was_running = pause and self.ci_status["running"]
                if self.ci_was_running:
                    sivm._stop_continuous_inference()
            def __exit__(self, type, value, traceback):
                if self.ci_was_running:
                    #print("restarting continuous inference")
                    sivm._start_continuous_inference(self.ci_status["params"])
        return tmp()


    ###############################
    # Continuous Inference on/off
    ###############################
    
    def _init_continuous_inference(self):
        pass
    
    def _continuous_inference_status(self):
        return self._call_core_sivm_instruction({"instruction" : "continuous_inference_status"})

    def _start_continuous_inference(self, params):
        self._call_core_sivm_instruction({"instruction" : "start_continuous_inference", "params" : params})

    def _stop_continuous_inference(self):
        self._call_core_sivm_instruction({"instruction" : "stop_continuous_inference"})

    ###############################
    # Shortcuts
    ###############################

    def _validate_label(self, instruction, exists=False):
        label = utils.validate_arg(instruction,'label',
                utils.validate_symbol)
        if exists==False and label in self.label_dict:
            raise VentureException('invalid_argument',
                    'Label "{}" is already assigned to a different directive.'.format(label),
                    argument='label')
        if exists==True and label not in self.label_dict:
            raise VentureException('invalid_argument',
                    'Label "{}" does not exist.'.format(label),
                    argument='label')
        return label

    ###############################
    # labeled instruction wrappers
    ###############################
    
    def _do_labeled_directive(self, instruction):
        label = self._validate_label(instruction)
        tmp = instruction.copy()
        tmp['instruction'] = instruction['instruction'][len('labeled_'):]
        del tmp['label']
        response = self._call_core_sivm_instruction(tmp)
        did = response['directive_id']
        self.label_dict[label] = did
        self.did_dict[did] = label
        return response    
    
    _do_labeled_assume = _do_labeled_directive
    _do_labeled_observe = _do_labeled_directive
    _do_labeled_predict = _do_labeled_directive    
    
    def _do_labeled_operation(self, instruction):
        label = self._validate_label(instruction, exists=True)
        tmp = instruction.copy()
        tmp['instruction'] = instruction['instruction'][len('labeled_'):]
        tmp['directive_id'] = self.label_dict[instruction['label']]
        del tmp['label']
        return self._call_core_sivm_instruction(tmp)        
    
    _do_labeled_forget = _do_labeled_operation
    _do_labeled_report = _do_labeled_operation
    _do_labeled_get_logscore = _do_labeled_operation

    ###############################
    # new instructions
    ###############################
    
    # adds label back to directive
    def get_directive(self, did):
        tmp = copy.deepcopy(self.directive_dict[did])
        if did in self.did_dict:
            tmp['label'] = self.did_dict[did]
            #tmp['instruction'] = 'labeled_' + tmp['instruction']
        return tmp
    
    def _do_list_directives(self, _):
        return { "directives" : [self.get_directive(did) for did in self.directive_dict.keys()] }
    
    def _do_get_directive(self, instruction):
        did = utils.validate_arg(instruction, 'directive_id', utils.validate_positive_integer)
        if not did in self.directive_dict:
            raise VentureException('invalid_argument',
                    "Directive with directive_id = {} does not exist".format(did),
                    argument='directive_id')
        return {"directive": self.get_directive(did)}
    
    def _do_labeled_get_directive(self, instruction):
        label = self._validate_label(instruction, exists=True)
        did = self.label_dict[label]
        return {"directive":self.get_directive(did)}
    
    def _do_force(self, instruction):
        exp = utils.validate_arg(instruction,'expression',
                utils.validate_expression, wrap_exception=False)
        val = utils.validate_arg(instruction,'value',
                utils.validate_value)
        inst1 = {
                "instruction" : "observe",
                "expression" : exp,
                "value" : val,
                }
        o1 = self._call_core_sivm_instruction(inst1)
        inst2 = {
                "instruction" : "forget",
                "directive_id" : o1['directive_id'],
                }
        self._call_core_sivm_instruction(inst2)
        return {}
    
    def _do_sample(self, instruction):
        exp = utils.validate_arg(instruction,'expression',
                utils.validate_expression, wrap_exception=False)
        inst1 = {
                "instruction" : "predict",
                "expression" : exp,
                }
        o1 = self._call_core_sivm_instruction(inst1)
        inst2 = {
                "instruction" : "forget",
                "directive_id" : o1['directive_id'],
                }
        self._call_core_sivm_instruction(inst2)
        return {"value":o1['value']}
    
    # not used anymore?
    def _do_continuous_inference_configure(self, instruction):
        d = utils.validate_arg(instruction,'options',
                utils.validate_dict, required=False)
        enable_ci = utils.validate_arg(d,'continuous_inference_enable',
                utils.validate_boolean, required=False)
        if enable_ci != None:
            if enable_ci == True and self._continuous_inference_enabled() == False:
                self._enable_continuous_inference()
            if enable_ci == False and self._continuous_inference_enabled() == True:
                self._disable_continuous_inference()
        return {"options":{
                "continuous_inference_enable" : self._continuous_inference_enabled(),
                }}
    
    def _do_get_current_exception(self, _):
        utils.require_state(self.state,'exception','paused')
        return {
                'exception': copy.deepcopy(self.current_exception),
                }
    
    def _do_get_state(self, _):
        return {
                'state': self.state,
                }
    
    def _do_reset(self, instruction):
        if self.state != 'default':
            instruction = {
                    'instruction': 'rollback',
                    }
            self._call_core_sivm_instruction(instruction)
        instruction = {
                'instruction': 'clear',
                }
        self._call_core_sivm_instruction(instruction)
        return {}
    
    def _do_debugger_list_breakpoints(self, _):
        return {
                "breakpoints" : copy.deepcopy(self.breakpoint_dict.values()),
                }
    
    def _do_debugger_get_breakpoint(self, instruction):
        bid = utils.validate_arg(instruction,'breakpoint_id',
                utils.validate_positive_integer)
        if not bid in self.breakpoint_dict:
            raise VentureException('invalid_argument',
                    "Breakpoint with breakpoint_id = {} does not exist".format(bid),
                    argument='breakpoint_id')
        return {"breakpoint":copy.deepcopy(self.breakpoint_dict[bid])}

