import orjson
from pathlib import Path


class Glossary:
    def __init__(self):
        self._names = []
        self._gsy_type = {}
        self._desc = {}
        self._text = {}

    @property
    def names(self):
        return self._names

    @names.setter
    def names(self, n):
        self._names = n

    @property
    def gsy_type(self):
        return self._gsy_type

    @gsy_type.setter
    def gsy_type(self, t):
        self._gsy_type = t

    @property
    def desc(self):
        return self._desc

    @desc.setter
    def desc(self, d):
        self._desc = d

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, t):
        self._text = t

    @classmethod
    def from_json(cls, json_obj: dict):
        glsry_insts = cls()

        for glsr_d in json_obj["glossary"]:
            g_n = glsr_d["term"]
            g_tp = glsr_d["type"]
            g_desc = glsr_d["description"]
            if isinstance(g_desc, list):
                p_desc = ", ".join(g_desc)
            else:
                p_desc = g_desc

            if g_n in glsry_insts.names:
                pass
            else:
                glsry_insts.names.append(g_n)
                glsry_insts.gsy_type[g_n] = g_tp
                glsry_insts.desc[g_n] = p_desc
                g_text = f"{g_n} is a {g_tp} term that refers {p_desc}"
                glsry_insts.text[g_n] = g_text
        return glsry_insts


class OpCode:
    def __init__(self):
        self._cmd_names = []
        self._cmd_port_map = {}
        self._port_cmd_text_map = {}
        self._cmd_on_port_text_map = {}

    @property
    def cmd_names(self):
        return self._cmd_names

    @cmd_names.setter
    def cmd_names(self, c_l):
        self._cmd_names = c_l

    @property
    def cmd_port_map(self):
        return self._cmd_port_map

    @cmd_port_map.setter
    def cmd_port_map(self, cpm):
        self._cmd_port_map = cpm

    @property
    def port_cmd_text_map(self):
        return self._port_cmd_text_map

    @port_cmd_text_map.setter
    def port_cmd_text_map(self, pcm):
        self._port_cmd_text_map = pcm

    @property
    def cmd_on_port_text_map(self):
        return self._cmd_on_port_text_map

    @cmd_on_port_text_map.setter
    def cmd_on_port_text_map(self, cmd_d):
        self._cmd_on_port_text_map = cmd_d

    def _gen_cmd_on_port(self):
        new_d = {}
        for port, cmd_map in self.port_cmd_text_map.items():
            for cmd, text in cmd_map.items():
                new_k = f"{cmd}-on-{port}"
                new_d.update({new_k: text})

        self.cmd_on_port_text_map = new_d

    @classmethod
    def from_json(cls, json_obj: dict):
        op_code_i = cls()
        cmd_l = json_obj["design_overview"]["opcode_mapping"]["commands"]
        for cmd_d in cmd_l:
            port_l = []
            op_code_i.cmd_names.append(cmd_d["name"])
            cmd_n = cmd_d["name"]
            op_type = cmd_d["opcode_type"]
            r_edge_d = cmd_d["clock_edges"]["rising"]
            f_edge_d = cmd_d["clock_edges"]["falling"]
            for p_m in r_edge_d["port_mapping"]:
                port_n = p_m["port_name"]
                if port_n in port_l:
                    pass
                else:
                    port_l.append(port_n)

                code_text = " or ".join(p_m["code"])
                expln_text = ", ".join(p_m["explain"])
                # **the rising edge is hard-coding and maybe a risk later**
                p_md_txt = (f"The command {cmd_n} on port {port_n} is "
                            f"{op_type}, and active at clock's rising edge."
                            f"Command {cmd_n} encoding on {port_n} is "
                            f"{code_text} for the command phrase, please "
                            f"refer {expln_text }.")
                if port_n in op_code_i.port_cmd_text_map:
                    cmd_txt_d = op_code_i.port_cmd_text_map[port_n]
                    cmd_txt_d.update({cmd_n: p_md_txt})
                else:
                    cmd_txt_d = {cmd_n: p_md_txt}
                    op_code_i.port_cmd_text_map[port_n] = cmd_txt_d

            for p_m in f_edge_d["port_mapping"]:
                port_n = p_m["port_name"]
                if port_n in port_l:
                    pass
                else:
                    port_l.append(port_n)

                code_text = " or ".join(p_m["code"])
                expln_text = ", ".join(p_m["explain"])
                # **The falling edge is hard-coding and may be a risk later**
                p_md_txt = (f"The command {cmd_n} on port {port_n} is "
                            f"{op_type}, and active at clock's falling edge. "
                            f"Command {cmd_n} encoding on "
                            f"{port_n} is {code_text} for the command phrase, "
                            f"please refer {expln_text}.")
                if port_n in op_code_i.port_cmd_text_map:
                    cmd_txt_d = op_code_i.port_cmd_text_map[port_n]
                    cmd_txt_d.update({cmd_n: p_md_txt})
                    op_code_i.port_cmd_text_map[port_n] = cmd_txt_d
                else:
                    cmd_txt_d = {cmd_n: p_md_txt}
                    op_code_i.port_cmd_text_map[port_n] = cmd_txt_d

            op_code_i.cmd_port_map[cmd_n] = port_l
            op_code_i._gen_cmd_on_port()
        return op_code_i


class PortInfo:
    def __init__(self):
        self._ports = []
        self._port_io = {}
        self._port_width = {}
        self._port_domain = {}
        self._port_desc = {}
        self._port_type = {}
        self._port_sync = {}
        self._port_text = {}

    @property
    def ports(self):
        return self._ports

    @ports.setter
    def ports(self, p_l):
        self._ports = p_l

    @property
    def port_io(self):
        return self._port_io

    @port_io.setter
    def port_io(self, io_dict):
        self._port_io = io_dict

    @property
    def port_width(self):
        return self._port_width

    @port_width.setter
    def port_width(self, width_dict):
        self._port_width = width_dict

    @property
    def port_domain(self):
        return self._port_domain

    @port_domain.setter
    def port_domain(self, domain_dict):
        self._port_domain = domain_dict

    @property
    def port_desc(self):
        return self._port_desc

    @port_desc.setter
    def port_desc(self, desc_dict):
        self._port_desc = desc_dict

    @property
    def port_type(self):
        return self._port_type

    @port_type.setter
    def port_type(self, type_dict):
        self._port_type = type_dict

    @property
    def port_sync(self):
        return self._port_sync

    @port_sync.setter
    def port_sync(self, sync_dict):
        self._port_sync = sync_dict

    @property
    def port_text(self):
        return self._port_text

    @port_text.setter
    def port_text(self, text_dict):
        self._port_text = text_dict

    @classmethod
    def from_json(cls, json_obj: dict):
        p_ist = cls()
        dsgn_obj = json_obj["design_overview"]
        p_desc = dsgn_obj["port_description"]
        for port_info in dsgn_obj["port_definition"]:
            p_nm = port_info["port_name"]
            p_ist.ports.append(p_nm)
            p_ist.port_io[p_nm] = port_info["port_io"]
            p_ist.port_width[p_nm] = port_info["port_width"]
            p_ist.port_domain[p_nm] = port_info["clock_domain"]
            p_ist.port_type[p_nm] = port_info["type"]
            p_ist.port_sync[p_nm] = port_info["is_registered"]

        for p_d in p_desc:
            if isinstance(p_d["description"], list):
                dsc = ",".join(p_d["description"])
            else:
                dsc = p_d["description"]

            p_ist.port_desc[p_d["port_name"]] = dsc

        for p_n in p_ist.ports:
            io = p_ist.port_io[p_n]
            width = p_ist.port_width[p_n]
            domain = p_ist.port_domain[p_n]
            desc = p_ist.port_desc[p_n]
            typ = p_ist.port_type[p_n]
            syn = p_ist.port_sync[p_n]
            if width > 1:
                width_str = f"[{width-1}:0]"
            else:
                width_str = ""

            if syn:
                p_text = f"""
{p_n}{width_str} is {io} port, its clock domain is {domain}, The function of 
{p_n} is {desc}. Attention: {p_n} need be synchronized by internal register!
                          """
            else:
                p_text = f"""
{p_n}{width_str} is {io} port, its clock domain is {domain}, The function of 
{p_n} is {desc}. Attention: {p_n} do not need be synchronized by internal 
register!
                          """
            p_ist.port_text[p_n] = p_text
        return p_ist


class StateInfo:
    def __init__(self, name):
        self._name = name
        self._type = ""
        self._next_states = []
        self._transitions = {}
        self._behavior_text = ""

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, n):
        self._name = n

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, t):
        self._type = t

    @property
    def next_states(self):
        return self._next_states

    @next_states.setter
    def next_states(self, n_s):
        self._next_states = n_s

    @property
    def transitions(self):
        return self._transitions

    @transitions.setter
    def transitions(self, t_dict):
        self._transitions = t_dict

    @property
    def behavior_text(self):
        return self._behavior_text

    @behavior_text.setter
    def behavior_text(self, b):
        self._behavior_text = b


class StateMachineInfo:
    def __init__(self):
        self._name = ""
        self._init_state = None
        self._states = []
        self._states_inst = {}
        self._states_text = {}

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, n):
        self._name = n

    @property
    def init_state(self):
        return self._init_state

    @init_state.setter
    def init_state(self, i_s):
        self._init_state = i_s

    @property
    def states(self):
        return self._states

    @states.setter
    def states(self, s_l):
        self._states = s_l

    @property
    def states_inst(self):
        return self._states_inst

    @states_inst.setter
    def states_inst(self, s_i_d):
        self._states_inst = s_i_d

    @property
    def states_text(self):
        return self._states_text

    @states_text.setter
    def states_text(self, s_t_d):
        self._states_text = s_t_d

    @classmethod
    def from_json(cls, json_obj: dict):
        fsm_inst = cls()
        st_d = json_obj["design_overview"]["functionality"]["state_machine"]
        fsm_inst.name = st_d["name"]
        for sin_st in st_d["states"]:
            fsm_inst.states.append(sin_st["name"])
            st_i = StateInfo(sin_st["name"])
            st_tp = sin_st["type"]
            if st_tp == "initial":
                st_i.type = "initial"
                fsm_inst.init_state = st_i.name
            elif st_tp == "normal":
                st_i.type = "normal"
            else:
                # TODO handle the waring
                print("warning")

            for trast in sin_st["transitions"]:
                nx_sts = trast["next_state"]
                st_i.next_states.append(nx_sts)
                trst_cndton = trast["condition"]
                st_i.transitions.update({nx_sts: trst_cndton})
            if isinstance(sin_st["behavior"][0], dict):
                # check if the behavior has multiple modes.
                st_txt_l = []
                for b_d in sin_st["behavior"]:
                    if isinstance(b_d["action"], list):
                        ac_txt = ", ".join(b_d["action"])
                    else:
                        ac_txt = b_d["action"]
                    sin_txt = f"when {b_d['condition']}, {ac_txt}"
                    st_txt_l.append(sin_txt)
                st_i.behavior_text = "\n".join(st_txt_l)
            else:
                # the behavior only one mode
                ac_txt = ", ".join(sin_st["behavior"])
                st_i.behavior_text = ac_txt

            fsm_inst.states_inst.update({st_i.name: st_i})
            tran_txt_l= []
            for nx_st, nx_cnd in st_i.transitions.items():
                tran_txt_l.append(f"when {nx_cnd}, {st_i.name} will transition"
                                  f" to {nx_st}")
            tran_txt = ", ".join(tran_txt_l)
            stat_txt = (f"{st_i.name} is {st_i.type} state in State Machine, "
                        f"{tran_txt}, While in this state,Operations are "
                        f"{st_i.behavior_text}")
            fsm_inst.states_text.update({st_i.name: stat_txt})
        return fsm_inst


class SpecInfo:
    def __init__(self):
        self._op_code = None
        self._port_info = None
        self._fsm_info = None
        self._glossary = None

    @property
    def op_code(self):
        return self._op_code

    @op_code.setter
    def op_code(self, o_c):
        self._op_code = o_c

    @property
    def port_info(self):
        return self._port_info

    @port_info.setter
    def port_info(self, p_i):
        self._port_info = p_i

    @property
    def fsm_info(self):
        return self._fsm_info

    @fsm_info.setter
    def fsm_info(self, f_i):
        self._fsm_info = f_i

    @property
    def glossary(self):
        return self._glossary

    @glossary.setter
    def glossary(self, v_i):
        self._glossary = v_i

    @classmethod
    def from_json(cls, json_path: str):
        json_p = Path(json_path)
        json_str = json_p.read_text()
        json_obj = orjson.loads(json_str)
        spec_info_i = cls()
        op_code_i = OpCode.from_json(json_obj)
        spec_info_i.op_code = op_code_i
        port_info_i = PortInfo.from_json(json_obj)
        spec_info_i.port_info = port_info_i
        fsm_info_i = StateMachineInfo.from_json(json_obj)
        spec_info_i.fsm_info = fsm_info_i
        glossary_i = Glossary.from_json(json_obj)
        spec_info_i.glossary = glossary_i
        return spec_info_i
