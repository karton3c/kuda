# Kuda v0.2.10 - C Code Generator with Full Builtins Support
from parser import *
import math

class CompileError(Exception):
    def __init__(self, msg, line=None):
        prefix = f'[Kuda CompileError] Line {line}: ' if line else '[Kuda CompileError] '
        super().__init__(f'{prefix}{msg}')


class CGenerator:
    # Known C libraries: use name -> gcc flags
    C_LIBS = {
        'sdl2':    ['-lSDL2', '-I/usr/include/SDL2'],
        'SDL2':    ['-lSDL2', '-I/usr/include/SDL2'],
        'gl':      ['-lGL'],
        'GL':      ['-lGL'],
        'glew':    ['-lGLEW'],
        'GLEW':    ['-lGLEW'],
        'glfw':    ['-lglfw'],
        'openal':  ['-lopenal'],
        'pthread': ['-lpthread'],
        'curl':    ['-lcurl'],
        'sqlite3': ['-lsqlite3'],
        'ncurses': ['-lncurses'],
    }

    def __init__(self):
        self.lines = []
        self.indent = 0
        self.tmp_count = 0
        self.vars = {}
        self.functions = {}
        self.includes = set()
        self.models = {}
        self.link_flags = []  # extra gcc flags collected from use statements
        self.extern_decls = []  # extern C function declarations
        self.extern_funcs = {}  # name -> ret_type for extern functions
        self.extra_c_files = []  # .c files to compile alongside main

    def fresh_tmp(self):
        self.tmp_count += 1
        return f'_t{self.tmp_count}'

    def emit(self, line=''):
        self.lines.append('    ' * self.indent + line)

    def _uses_data_builder(self, ast):
        """Check if AST uses data builder — if so, fall back to interpreter."""
        import ast as pyast
        src = str([(type(s).__name__, getattr(s, '__dict__', {})) for s in ast.statements])
        # Simple check: walk all nodes looking for IdentNode with name 'data'
        def _check(node):
            if isinstance(node, IdentNode) and node.name == 'data':
                return True
            for attr in vars(node).values() if hasattr(node, '__dict__') else []:
                if hasattr(attr, '__dict__') and _check(attr): return True
                if isinstance(attr, list):
                    for item in attr:
                        if hasattr(item, '__dict__') and _check(item): return True
            return False
        for stmt in ast.statements:
            if _check(stmt): return True
        return False

    def _expand_uses(self, ast, source_file=None):
        """Recursively expand use "file.kuda" by inlining the file's AST."""
        import os
        from lexer import Lexer as _Lex
        from parser import Parser as _Par, ProgramNode as _ProgNode
        expanded = []
        for stmt in ast.statements:
            if isinstance(stmt, UseNode) and stmt.filepath is not None:
                if stmt.absolute:
                    path = os.path.abspath(stmt.filepath)
                else:
                    base = source_file or os.getcwd()
                    if os.path.isfile(base):
                        base = os.path.dirname(base)
                    path = os.path.join(base, stmt.filepath)
                path = os.path.normpath(path)
                if not os.path.exists(path):
                    raise CompileError(f"use: plik nie istnieje: '{path}'", getattr(stmt, 'line', None))
                with open(path, 'r', encoding='utf-8') as f:
                    src = f.read()
                sub_ast = _Par(_Lex(src).tokenize()).parse()
                # Recursively expand nested uses relative to this file
                sub_ast = self._expand_uses(sub_ast, path)
                expanded.extend(sub_ast.statements)
            else:
                expanded.append(stmt)
        ast.statements = expanded
        return ast

    def generate(self, ast, source_file=None):
        self.includes.add('#include <stdio.h>')
        self.includes.add('#include <stdlib.h>')
        self.includes.add('#include <string.h>')
        self.includes.add('#include <math.h>')
        self.includes.add('#include <time.h>')
        self.includes.add('#include <unistd.h>')
        self.includes.add('#include <ctype.h>')
        self.includes.add('#include <stdint.h>')

        # Expand use "file.kuda" statements by inlining their AST
        ast = self._expand_uses(ast, source_file)

        func_decls = []
        model_decls = []
        net_decls = []
        net_load_decls = []
        main_stmts = []
        for stmt in ast.statements:
            if isinstance(stmt, FunNode):
                func_decls.append(stmt)
            elif isinstance(stmt, ModelNode):
                model_decls.append(stmt)
            elif isinstance(stmt, NetNode):
                net_decls.append(stmt)
                main_stmts.append(stmt)  # keep in order as sentinel
            elif isinstance(stmt, NetLoadNode):
                net_load_decls.append(stmt)
                main_stmts.append(stmt)  # keep in order as sentinel
            else:
                main_stmts.append(stmt)

        # First pass: register all models so we know their names
        for m in model_decls:
            self.models[m.name] = {}  # will be filled in _gen_model

        # Register function return types before scanning call sites
        self.func_return_types = {}  # func_name -> return type
        for f in func_decls:
            ret = self._scan_return_type(f.body)
            self.func_return_types[f.name] = ret

        # Deep pre-scan: build global variable type map from ALL assignments
        self.func_param_types = {}
        global_var_types = {}
        self._deep_prescan(ast.statements, global_var_types)

        # Third pass: scan call sites with enriched type info
        self._scan_call_sites(ast.statements)

        runtime = self._runtime()

        # Generate model structs and methods
        model_code = []
        for m in model_decls:
            model_code.extend(self._gen_model(m))

        # Generate net structs and training code
        net_code = []
        net_var_types = {}  # net_name -> struct info
        self._net_info = {}
        for n in net_decls:
            nc, ninfo = self._gen_net(n, main_stmts)
            net_code.extend(nc)
            net_var_types[n.name] = ninfo
            self._net_info[n.name] = ninfo
            self.vars[n.name] = 'net'

        for n in net_load_decls:
            nc, ninfo = self._gen_net_load_decl(n)
            net_code.extend(nc)
            net_var_types[n.name] = ninfo
            self._net_info[n.name] = ninfo
            self.vars[n.name] = 'net'

        func_code = []
        for f in func_decls:
            func_code.extend(self._gen_function(f))

        # Register net names so they're known during prescan
        for n in net_decls:
            self.vars[n.name] = 'net'
        for n in net_load_decls:
            self.vars[n.name] = 'net'

        # Pre-declare all variables in main
        pre = self._prescan_vars(main_stmts, set())

        self.emit('int main(int argc, char *argv[]) {')
        self.indent += 1
        self.emit('srand(time(NULL));')
        for vname, vtyp in pre.items():
            self.vars[vname] = vtyp
            if vtyp == 'str':          self.emit(f'char* {vname} = NULL;')
            elif vtyp == 'bool':       self.emit(f'int {vname} = 0;')
            elif vtyp in ('list', 'strlist'):  self.emit(f'KList* {vname} = NULL;')
            elif vtyp in self.models:  self.emit(f'{vtyp}* {vname} = NULL;')
            elif vtyp == 'net':        pass  # net structs declared in net_code
            else:                      self.emit(f'double {vname} = 0;')
        for stmt in main_stmts:
            self._gen_stmt(stmt)
        self.emit('return 0;')
        self.indent -= 1
        self.emit('}')

        main_code = self.lines
        final = []
        final.extend(sorted(self.includes))
        final.append('')
        if self.extern_decls:
            final.extend(self.extern_decls)
            final.append('')
        final.extend(runtime)
        final.append('')
        final.extend(model_code)
        final.append('')
        final.extend(net_code)
        final.append('')
        final.extend(func_code)
        final.append('')
        final.extend(main_code)
        return '\n'.join(final)

    def _deep_prescan(self, stmts, var_types):
        """
        Walk ALL statements recursively and build a complete map of
        variable_name -> type for the whole program. This runs before
        code generation so we know types of every variable everywhere.
        """
        STR_FUNCS = {'input', 'str', 'caps', 'small', 'trim', 'swap', 'merge', 'read'}
        LIST_FUNCS = {'cut', 'softmax', 'xav', 'he', 'snip', 'pack', 'shuffle'}
        STRLIST_FUNCS = {'readlines'}

        def is_str_expr(node):
            if isinstance(node, StringNode): return True
            if isinstance(node, BinOpNode) and node.op == '+':
                return is_str_expr(node.left) or is_str_expr(node.right)
            if isinstance(node, CallNode) and isinstance(node.func, IdentNode):
                fname = node.func.name
                if fname in STR_FUNCS: return True
                if self.func_return_types.get(fname) == 'str': return True
            if isinstance(node, IdentNode):
                return var_types.get(node.name) == 'str' or self.vars.get(node.name) == 'str'
            return False

        for node in stmts:
            if isinstance(node, AssignNode) and isinstance(node.name, str):
                v = node.name
                if isinstance(node.value, StringNode):
                    var_types[v] = 'str'
                elif is_str_expr(node.value):
                    var_types[v] = 'str'
                elif isinstance(node.value, (ListNode, ListCompNode)):
                    if isinstance(node.value, ListNode):
                        has_str = any(isinstance(e, StringNode) for e in node.value.elements)
                        var_types[v] = 'strlist' if has_str else 'list'
                    else:
                        var_types[v] = 'list'
                elif isinstance(node.value, CallNode) and isinstance(node.value.func, IdentNode):
                    fname = node.value.func.name
                    if fname in self.models:
                        var_types[v] = fname
                    elif fname in self.func_return_types and self.func_return_types[fname] in self.models:
                        var_types[v] = self.func_return_types[fname]
                    elif fname in STR_FUNCS or self.func_return_types.get(fname) == 'str':
                        var_types[v] = 'str'
                    elif fname in LIST_FUNCS or self.func_return_types.get(fname) == 'list':
                        var_types[v] = 'list'
                    elif fname in STRLIST_FUNCS:
                        var_types[v] = 'strlist'
                    else:
                        var_types.setdefault(v, 'double')
                elif isinstance(node.value, AttrNode):
                    # Sprawdź czy to data builder chain (data.binary.sequential.xor itp.)
                    def _is_data_chain(n):
                        if isinstance(n, IdentNode) and n.name == 'data': return True
                        if isinstance(n, AttrNode): return _is_data_chain(n.obj)
                        if isinstance(n, CallNode): return _is_data_chain(n.func)
                        return False
                    if _is_data_chain(node.value):
                        var_types[v] = 'list'
                    else:
                        var_types.setdefault(v, 'double')
                else:
                    var_types.setdefault(v, 'double')
                # Update self.vars so _scan_call_sites can see them
                self.vars[v] = var_types[v]
            if isinstance(node, FunNode):    self._deep_prescan(node.body, var_types)
            if isinstance(node, ModelNode):
                for s in node.body:
                    if isinstance(s, FunNode): self._deep_prescan(s.body, var_types)
            if isinstance(node, IfNode):
                for _, body in node.cases: self._deep_prescan(body, var_types)
                if node.else_body: self._deep_prescan(node.else_body, var_types)
            if isinstance(node, RepeatNode): self._deep_prescan(node.body, var_types)
            if isinstance(node, EachNode):
                var_types[node.var] = 'double'
                self._deep_prescan(node.body, var_types)
            if isinstance(node, TilNode):    self._deep_prescan(node.body, var_types)

    def _scan_call_sites(self, stmts):
        """Scan all statements to find how functions are called and what types they receive."""
        STR_FUNCS = {'input', 'str', 'caps', 'small', 'trim', 'swap', 'merge', 'read'}
        LIST_FUNCS = {'cut', 'softmax', 'xav', 'he', 'snip', 'pack', 'shuffle'}
        STRLIST_FUNCS = {'readlines'}

        def is_str_expr(arg):
            if isinstance(arg, StringNode): return True
            if isinstance(arg, BinOpNode) and arg.op == '+':
                return is_str_expr(arg.left) or is_str_expr(arg.right)
            if isinstance(arg, CallNode) and isinstance(arg.func, IdentNode):
                fname = arg.func.name
                if fname in STR_FUNCS: return True
                if self.func_return_types.get(fname) == 'str': return True
            if isinstance(arg, IdentNode):
                return self.vars.get(arg.name) == 'str'
            return False

        def get_arg_type(arg):
            if is_str_expr(arg): return 'str'
            if isinstance(arg, IdentNode):
                return self.vars.get(arg.name, 'double')
            elif isinstance(arg, CallNode) and isinstance(arg.func, IdentNode):
                fname = arg.func.name
                if fname in self.models: return fname
                return self.func_return_types.get(fname, 'double')
            return 'double'

        def register_call(node):
            if isinstance(node, CallNode) and isinstance(node.func, IdentNode):
                fname = node.func.name
                arg_types = [get_arg_type(a) for a in node.args]
                existing = self.func_param_types.get(fname, [])
                merged = []
                for i in range(max(len(arg_types), len(existing))):
                    a = arg_types[i] if i < len(arg_types) else 'double'
                    e = existing[i] if i < len(existing) else 'double'
                    merged.append(a if (a in self.models or a == 'str') else e)
                self.func_param_types[fname] = merged

        def scan(stmts):
            for node in stmts:
                # Scan calls at statement level AND inside assignment RHS
                register_call(node)
                if isinstance(node, AssignNode):
                    register_call(node.value)
                if isinstance(node, OutNode):
                    register_call(node.value)
                if isinstance(node, GiveNode):
                    register_call(node.value)

                if isinstance(node, FunNode):    scan(node.body)
                if isinstance(node, ModelNode):
                    for s in node.body:
                        if isinstance(s, FunNode): scan(s.body)
                if isinstance(node, IfNode):
                    for _, body in node.cases: scan(body)
                    if node.else_body: scan(node.else_body)
                if isinstance(node, RepeatNode): scan(node.body)
                if isinstance(node, EachNode):   scan(node.body)
                if isinstance(node, TilNode):    scan(node.body)

        scan(stmts)

    def _runtime(self):
        return [
            '/* Kuda v0.2.10 Runtime - Full Featured */',
            '#define MAX_STR  4096',
            '#define MAX_MAT  512',
            '#define MAX_LIST 1024',
            '',
            '/* Dynamic List Type */',
            'typedef struct {',
            '    double* data;',
            '    int len;',
            '    int cap;',
            '} KList;',
            '',
            'KList* kuda_list_new() {',
            '    KList* l = malloc(sizeof(KList));',
            '    l->cap = 16;',
            '    l->len = 0;',
            '    l->data = malloc(sizeof(double) * l->cap);',
            '    return l;',
            '}',
            '',
            'void kuda_list_add(KList* l, double v) {',
            '    if (l->len >= l->cap) {',
            '        l->cap *= 2;',
            '        l->data = realloc(l->data, sizeof(double) * l->cap);',
            '    }',
            '    l->data[l->len++] = v;',
            '}',
            '',
            '/* Store a pointer (e.g. nested KList*) as a double slot via intptr_t */',
            'void kuda_list_add_ptr(KList* l, void* ptr) {',
            '    if (l->len >= l->cap) {',
            '        l->cap *= 2;',
            '        l->data = realloc(l->data, sizeof(double) * l->cap);',
            '    }',
            '    l->data[l->len++] = (double)(intptr_t)ptr;',
            '}',
            'KList* kuda_list_grab_ptr(KList* l, int idx) {',
            '    if (idx < 0 || idx >= l->len) return NULL;',
            '    return (KList*)(intptr_t)l->data[idx];',
            '}',
            '',
            'double kuda_list_grab(KList* l, int idx) {',
            '    if (idx < 0 || idx >= l->len) return 0;',
            '    return l->data[idx];',
            '}',
            '',
            'double kuda_list_pop(KList* l) {',
            '    if (l->len <= 0) return 0;',
            '    return l->data[--l->len];',
            '}',
            '',
            'void kuda_list_del(KList* l, double val) {',
            '    for (int i = 0; i < l->len; i++) {',
            '        if (l->data[i] == val) {',
            '            for (int j = i; j < l->len - 1; j++) l->data[j] = l->data[j+1];',
            '            l->len--;',
            '            return;',
            '        }',
            '    }',
            '}',
            '',
            'void kuda_list_sort(KList* l) {',
            '    for (int i = 0; i < l->len - 1; i++) {',
            '        for (int j = i + 1; j < l->len; j++) {',
            '            if (l->data[i] > l->data[j]) {',
            '                double t = l->data[i];',
            '                l->data[i] = l->data[j];',
            '                l->data[j] = t;',
            '            }',
            '        }',
            '    }',
            '}',
            '',
            'void kuda_list_rev(KList* l) {',
            '    for (int i = 0; i < l->len / 2; i++) {',
            '        double t = l->data[i];',
            '        l->data[i] = l->data[l->len - 1 - i];',
            '        l->data[l->len - 1 - i] = t;',
            '    }',
            '}',
            '',
            'int kuda_list_fd(KList* l, double val) {',
            '    for (int i = 0; i < l->len; i++) {',
            '        if (l->data[i] == val) return i;',
            '    }',
            '    return -1;',
            '}',
            '',
            'int kuda_list_cnt(KList* l, double val) {',
            '    int count = 0;',
            '    for (int i = 0; i < l->len; i++) {',
            '        if (l->data[i] == val) count++;',
            '    }',
            '    return count;',
            '}',
            '',
            'typedef struct { double data[MAX_MAT][MAX_MAT]; int rows; int cols; } KMatrix;',
            '',
            '/* Print */',
            'void kuda_print_double(double v) {',
            '    if (v == (long long)v && v > -1e15 && v < 1e15) printf("%lld\\n", (long long)v);',
            '    else printf("%.6g\\n", v);',
            '}',
            'void kuda_print_str(const char* v) { printf("%s\\n", v); }',
            'void kuda_print_bool(int v) { printf("%s\\n", v ? "True" : "False"); }',
            'void kuda_print_list(KList* l) {',
            '    printf("[");',
            '    for (int i = 0; i < l->len; i++) {',
            '        if (l->data[i] == (long long)l->data[i]) printf("%lld", (long long)l->data[i]);',
            '        else printf("%.6g", l->data[i]);',
            '        if (i < l->len - 1) printf(", ");',
            '    }',
            '    printf("]\\n");',
            '}',
            'char* kuda_list_to_str(KList* l) {',
            '    char buf[MAX_STR]; buf[0] = 0; strcat(buf, "[");',
            '    for (int i = 0; i < l->len; i++) {',
            '        char tmp[64];',
            '        if (l->data[i]==(long long)l->data[i]) sprintf(tmp,"%lld",(long long)l->data[i]);',
            '        else sprintf(tmp,"%.6g",l->data[i]);',
            '        strcat(buf, tmp);',
            '        if (i < l->len - 1) strcat(buf, ", ");',
            '    }',
            '    strcat(buf, "]"); char* r = strdup(buf); return r;',
            '}',
            'double kuda_list_sum(KList* l) {',
            '    double s = 0; for (int i = 0; i < l->len; i++) s += l->data[i]; return s;',
            '}',
            '',
            '/* Strings */',
            'char* kuda_concat(const char* a, const char* b) {',
            '    char* r = malloc(strlen(a)+strlen(b)+1);',
            '    strcpy(r,a); strcat(r,b); return r;',
            '}',
            'char* kuda_double_to_str(double v) {',
            '    char* r = malloc(64);',
            '    if (v==(long long)v && v>-1e15 && v<1e15) sprintf(r,"%lld",(long long)v);',
            '    else sprintf(r,"%.6g",v);',
            '    return r;',
            '}',
            'char* kuda_caps(const char* s) { char* r=strdup(s); for(int i=0;r[i];i++) r[i]=toupper((unsigned char)r[i]); return r; }',
            'char* kuda_small(const char* s) { char* r=strdup(s); for(int i=0;r[i];i++) r[i]=tolower((unsigned char)r[i]); return r; }',
            'char* kuda_trim(const char* s) {',
            '    while(*s==" "[0]||*s=="\\t"[0]) s++;',
            '    char* r=strdup(s); int l=strlen(r);',
            '    while(l>0&&(r[l-1]==" "[0]||r[l-1]=="\\t"[0])) r[--l]=0; return r;',
            '}',
            'char* kuda_swap(const char* s,const char* f,const char* t) {',
            '    char* r=malloc(MAX_STR); r[0]=0;',
            '    const char* p=s; int fl=strlen(f);',
            '    while(*p){ if(strncmp(p,f,fl)==0){strcat(r,t);p+=fl;}else{strncat(r,p,1);p++;} }',
            '    return r;',
            '}',
            '',
            '/* String cut (split) - returns list of strings encoded as doubles */',
            'KList* kuda_cut(const char* s, const char* delim) {',
            '    KList* result = kuda_list_new();',
            '    char* copy = strdup(s);',
            '    char* token = strtok(copy, delim);',
            '    while (token != NULL) {',
            '        // Store string pointer as double (we lose string functionality but match type system)',
            '        kuda_list_add(result, (double)(intptr_t)strdup(token));',
            '        token = strtok(NULL, delim);',
            '    }',
            '    free(copy);',
            '    return result;',
            '}',
            '',
            '/* String merge (join) */',
            'char* kuda_merge(const char* sep, KList* l) {',
            '    if (l->len == 0) return strdup("");',
            '    char* result = malloc(MAX_STR);',
            '    result[0] = 0;',
            '    for (int i = 0; i < l->len; i++) {',
            '        char* item = kuda_double_to_str(l->data[i]);',
            '        strcat(result, item);',
            '        if (i < l->len - 1) strcat(result, sep);',
            '        free(item);',
            '    }',
            '    return result;',
            '}',
            '',
            'int kuda_rand(int lo,int hi){return lo+rand()%(hi-lo+1);}',
            'double kuda_rand_float(){return (double)rand()/RAND_MAX;}',
            'double kuda_rand_normal(double mean, double std) {',
            '    /* Box-Muller transform */',
            '    double u1 = ((double)rand()+1.0)/(RAND_MAX+1.0);',
            '    double u2 = ((double)rand()+1.0)/(RAND_MAX+1.0);',
            '    double z = sqrt(-2.0*log(u1)) * cos(2.0*3.14159265358979*u2);',
            '    return mean + std * z;',
            '}',
            'void kuda_shuffle(KList* l) {',
            '    for (int i = l->len - 1; i > 0; i--) {',
            '        int j = rand() % (i + 1);',
            '        double tmp = l->data[i];',
            '        l->data[i] = l->data[j];',
            '        l->data[j] = tmp;',
            '    }',
            '}',
            '/* AI - activation functions */',
            'double kuda_sigmoid(double x){return 1.0/(1.0+exp(-x));}',
            'double kuda_sigmoid_d(double x){return x*(1.0-x);}',
            'double kuda_tanh_act(double x){return tanh(x);}',
            'double kuda_tanh_d(double x){return 1.0-x*x;}',
            'double kuda_relu(double x){return x>0.0?x:0.0;}',
            'double kuda_relu_d(double x){return x>0.0?1.0:0.0;}',
            'double kuda_leaky(double x){return x>0.0?x:0.01*x;}',
            'double kuda_leaky_d(double x){return x>0.0?1.0:0.01;}',
            'double kuda_linear(double x){return x;}',
            'double kuda_linear_act(double x){return x;}',
            'double kuda_linear_d(double x){(void)x;return 1.0;}',
            'double kuda_clip(double x,double lo,double hi){return x<lo?lo:(x>hi?hi:x);}',
            '/* AI - list operations */',
            'double kuda_dot(KList* a,KList* b){double s=0;int n=a->len<b->len?a->len:b->len;for(int i=0;i<n;i++)s+=a->data[i]*b->data[i];return s;}',
            'double kuda_argmax(KList* l){int idx=0;for(int i=1;i<l->len;i++)if(l->data[i]>l->data[idx])idx=i;return (double)idx;}',
            'double kuda_argmin(KList* l){int idx=0;for(int i=1;i<l->len;i++)if(l->data[i]<l->data[idx])idx=i;return (double)idx;}',
            'double kuda_mean(KList* l){double s=0;for(int i=0;i<l->len;i++)s+=l->data[i];return s/l->len;}',
            'double kuda_norm(KList* l){double s=0;for(int i=0;i<l->len;i++)s+=l->data[i]*l->data[i];return sqrt(s);}',
            'KList* kuda_softmax(KList* l){KList* r=kuda_list_new();double s=0;for(int i=0;i<l->len;i++)s+=exp(l->data[i]);for(int i=0;i<l->len;i++)kuda_list_add(r,exp(l->data[i])/s);return r;}',
            '/* AI - weight init */',
            'KList* kuda_xav(int n_in,int n_out){KList* r=kuda_list_new();double std=sqrt(2.0/(n_in+n_out));for(int i=0;i<n_in*n_out;i++){double u1=(double)(rand()+1)/(RAND_MAX+1.0),u2=(double)(rand()+1)/(RAND_MAX+1.0);kuda_list_add(r,std*sqrt(-2.0*log(u1))*cos(2.0*3.14159265*u2));}return r;}',
            'KList* kuda_he(int n_in){KList* r=kuda_list_new();double std=sqrt(2.0/n_in);for(int i=0;i<n_in;i++){double u1=(double)(rand()+1)/(RAND_MAX+1.0),u2=(double)(rand()+1)/(RAND_MAX+1.0);kuda_list_add(r,std*sqrt(-2.0*log(u1))*cos(2.0*3.14159265*u2));}return r;}',
            '/* AI - metrics */',
            'double kuda_acc(KList* pred,KList* target){int c=0;for(int i=0;i<target->len;i++)if((int)round(pred->data[i])==(int)round(target->data[i]))c++;return (double)c/target->len;}',
            'double kuda_crent(KList* pred,KList* target){double s=0;for(int i=0;i<target->len;i++){double p=pred->data[i]<1e-15?1e-15:pred->data[i];s+=target->data[i]*log(p);}return -s/target->len;}',
            '/* AI - list ops */',
            'KList* kuda_list_concat(KList* a, KList* b) {',
            '    KList* r = kuda_list_new();',
            '    for(int i=0;i<a->len;i++) kuda_list_add(r, a->data[i]);',
            '    for(int i=0;i<b->len;i++) kuda_list_add(r, b->data[i]);',
            '    return r;',
            '}',
            '',
            '',
            'char* kuda_input(const char* p){',
            '    printf("%s",p); char* b=malloc(MAX_STR);',
            '    if(!fgets(b,MAX_STR,stdin)) b[0]=0;',
            '    int l=strlen(b); if(l>0&&b[l-1]=="\\n"[0]) b[l-1]=0; return b;',
            '}',
            '',
            '/* Matrix */',
            'KMatrix* kuda_mat_new(int r,int c){KMatrix* m=calloc(1,sizeof(KMatrix));m->rows=r;m->cols=c;return m;}',
            'KMatrix* kuda_mat_rand(int r,int c){',
            '    KMatrix* m=kuda_mat_new(r,c);',
            '    double sc=sqrt(2.0/(r+c));',
            '    for(int i=0;i<r;i++) for(int j=0;j<c;j++) m->data[i][j]=((double)rand()/RAND_MAX*2-1)*sc;',
            '    return m;',
            '}',
            'double kuda_mat_get(KMatrix* m,int r,int c){return m->data[r][c];}',
            'void   kuda_mat_set(KMatrix* m,int r,int c,double v){m->data[r][c]=v;}',
            'KMatrix* kuda_mat_mul(KMatrix* A,KMatrix* B){',
            '    KMatrix* C=kuda_mat_new(A->rows,B->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<B->cols;j++) for(int k=0;k<A->cols;k++)',
            '        C->data[i][j]+=A->data[i][k]*B->data[k][j];',
            '    return C;',
            '}',
            'KMatrix* kuda_mat_add(KMatrix* A,KMatrix* B){',
            '    KMatrix* C=kuda_mat_new(A->rows,A->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) C->data[i][j]=A->data[i][j]+B->data[i][j];',
            '    return C;',
            '}',
            'KMatrix* kuda_mat_sub(KMatrix* A,KMatrix* B){',
            '    KMatrix* C=kuda_mat_new(A->rows,A->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) C->data[i][j]=A->data[i][j]-B->data[i][j];',
            '    return C;',
            '}',
            'KMatrix* kuda_mat_scale(KMatrix* A,double s){',
            '    KMatrix* C=kuda_mat_new(A->rows,A->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) C->data[i][j]=A->data[i][j]*s;',
            '    return C;',
            '}',
            'KMatrix* kuda_mat_T(KMatrix* A){',
            '    KMatrix* C=kuda_mat_new(A->cols,A->rows);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) C->data[j][i]=A->data[i][j];',
            '    return C;',
            '}',
            'KMatrix* kuda_mat_hadamard(KMatrix* A,KMatrix* B){',
            '    KMatrix* C=kuda_mat_new(A->rows,A->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) C->data[i][j]=A->data[i][j]*B->data[i][j];',
            '    return C;',
            '}',
            'KMatrix* kuda_mat_copy(KMatrix* A){',
            '    KMatrix* C=kuda_mat_new(A->rows,A->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) C->data[i][j]=A->data[i][j];',
            '    return C;',
            '}',
            'void kuda_mat_print(KMatrix* m){',
            '    for(int i=0;i<m->rows;i++){',
            '        printf("[");',
            '        for(int j=0;j<m->cols;j++){ printf("%.4f",m->data[i][j]); if(j<m->cols-1) printf(", "); }',
            '        printf("]\\n");',
            '    }',
            '}',
            'double kuda_mat_sum(KMatrix* A){double s=0;for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) s+=A->data[i][j];return s;}',
            'double kuda_mat_mean(KMatrix* A){return kuda_mat_sum(A)/(A->rows*A->cols);}',
            'double kuda_mat_dot(KMatrix* A,KMatrix* B){double s=0;for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) s+=A->data[i][j]*B->data[i][j];return s;}',
            '',
            '/* Matrix activation functions (use scalar ones defined earlier) */',
            'KMatrix* kuda_mat_sigmoid(KMatrix* A){',
            '    KMatrix* C=kuda_mat_new(A->rows,A->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) C->data[i][j]=kuda_sigmoid(A->data[i][j]);',
            '    return C;',
            '}',
            'KMatrix* kuda_mat_sigmoid_deriv(KMatrix* A){',
            '    KMatrix* C=kuda_mat_new(A->rows,A->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++){double s=kuda_sigmoid(A->data[i][j]);C->data[i][j]=s*(1-s);}',
            '    return C;',
            '}',
            'KMatrix* kuda_mat_relu(KMatrix* A){',
            '    KMatrix* C=kuda_mat_new(A->rows,A->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) C->data[i][j]=kuda_relu(A->data[i][j]);',
            '    return C;',
            '}',
            'KMatrix* kuda_mat_relu_deriv(KMatrix* A){',
            '    KMatrix* C=kuda_mat_new(A->rows,A->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) C->data[i][j]=A->data[i][j]>0?1.0:0.0;',
            '    return C;',
            '}',
            'KMatrix* kuda_mat_tanh(KMatrix* A){',
            '    KMatrix* C=kuda_mat_new(A->rows,A->cols);',
            '    for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) C->data[i][j]=tanh(A->data[i][j]);',
            '    return C;',
            '}',
            '',
            '/* Loss */',
            'double kuda_mse_scalar(double p, double t){ double d=p-t; return d*d; }',
        'double kuda_mse(KMatrix* p,KMatrix* t){',
            '    double l=0; int n=p->rows*p->cols;',
            '    for(int i=0;i<p->rows;i++) for(int j=0;j<p->cols;j++){double d=p->data[i][j]-t->data[i][j];l+=d*d;}',
            '    return l/n;',
            '}',
            'KMatrix* kuda_mse_grad(KMatrix* p,KMatrix* t){',
            '    int n=p->rows*p->cols; KMatrix* C=kuda_mat_new(p->rows,p->cols);',
            '    for(int i=0;i<p->rows;i++) for(int j=0;j<p->cols;j++) C->data[i][j]=2.0*(p->data[i][j]-t->data[i][j])/n;',
            '    return C;',
            '}',
            '/* end Kuda runtime */',
        ]

    def _tmp_var(self):
        if not hasattr(self, '_tmp_counter'): self._tmp_counter = 0
        self._tmp_counter += 1
        return f'_kuda_tmp{self._tmp_counter}'

    def _gen_net(self, node, pre_stmts=None):
        """Delegate to net.py — generates C code for a net block."""
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from net import gen_net_c
        from interpreter import Interpreter
        interp = Interpreter()
        # Run only data-setup statements (e.g. data.cust = ...) before evaluating net params
        # Do NOT run out(), if, loops etc. — only pure assignments to 'data' attributes
        from parser import (NetNode as _NetNode, AssignNode as _AssignNode,
                            AttrNode as _AttrNode, IdentNode as _IdentNode,
                            CallNode as _CallNode, NumberNode as _NumberNode,
                            StringNode as _StringNode, ListNode as _ListNode)

        if pre_stmts:
            def _is_data_chain(n):
                """True if node is a data.binary(...).sequential.xor style chain."""
                if isinstance(n, _IdentNode) and n.name == 'data': return True
                if isinstance(n, _AttrNode):  return _is_data_chain(n.obj)
                if isinstance(n, _CallNode):  return _is_data_chain(n.func)
                return False

            def _is_safe_value(n):
                """True if node is safe to evaluate in the temp interpreter:
                   DataBuilder chains, literals, list literals, or ident refs."""
                if _is_data_chain(n):                return True
                if isinstance(n, (_NumberNode, _StringNode)): return True
                if isinstance(n, _IdentNode):        return True
                if isinstance(n, _ListNode):         return True
                return False

            for stmt in pre_stmts:
                if isinstance(stmt, _NetNode):
                    continue
                if not isinstance(stmt, _AssignNode):
                    continue
                is_data_attr = (isinstance(stmt.name, _AttrNode)
                                and isinstance(stmt.name.obj, _IdentNode)
                                and stmt.name.obj.name == 'data')
                is_safe_var = (isinstance(stmt.name, str)
                               and _is_safe_value(stmt.value))
                if not (is_data_attr or is_safe_var):
                    continue
                try:
                    interp.exec(stmt, interp.global_env)
                except Exception:
                    pass
        _ACT_NAMES  = {'tanh', 'sigmoid', 'relu', 'leaky', 'linear'}
        _INIT_NAMES = {'xav', 'he'}
        _runtime_inputs  = None
        _runtime_targets = None
        for key, val_node in node.params.items():
            if key == 'inputs' and isinstance(val_node, _IdentNode):
                try:
                    v = interp.eval(val_node, interp.global_env)
                    # If empty list or not a list-of-lists, treat as runtime variable
                    if not v or not isinstance(v, list) or not v or not isinstance(v[0], (list, tuple)):
                        _runtime_inputs = val_node.name
                except Exception:
                    _runtime_inputs = val_node.name
            if key == 'targets' and isinstance(val_node, _IdentNode):
                try:
                    v = interp.eval(val_node, interp.global_env)
                    if not v or not isinstance(v, list) or not v or not isinstance(v[0], (list, tuple)):
                        _runtime_targets = val_node.name
                except Exception:
                    _runtime_targets = val_node.name

        def eval_fn(val_node):
            if isinstance(val_node, _IdentNode):
                if val_node.name in _ACT_NAMES or val_node.name in _INIT_NAMES:
                    return val_node.name
            return interp.eval(val_node, interp.global_env)

        result_lines, ninfo = gen_net_c(node, eval_fn)

        # If inputs/targets are runtime KList* variables, patch the train function
        # to read data from them dynamically instead of static arrays
        if _runtime_inputs and _runtime_targets:
            name = node.name
            if not hasattr(self, '_dynamic_nets'):
                self._dynamic_nets = {}
            self._dynamic_nets[name] = (_runtime_inputs, _runtime_targets)
            result_lines = self._patch_net_dynamic_data(
                result_lines, name, _runtime_inputs, _runtime_targets, ninfo)

        return result_lines, ninfo

    def _patch_net_dynamic_data(self, lines, name, inputs_var, targets_var, ninfo):
        """Patch generated net C code to read inputs/targets from runtime KList* vars."""
        NAME = name.upper()
        n_in  = ninfo.get('n_inputs',  1)
        n_out = ninfo.get('n_outputs', 1)

        new_lines = []
        injected = False
        in_train = False

        for line in lines:
            # Remove static data array declarations
            if (f'static double {name}_data_in[]' in line or
                    f'static double {name}_data_tgt[]' in line):
                continue

            # Replace n_samples static decl with 0
            if f'static int    {name}_n_samples' in line:
                new_lines.append(f'static int    {name}_n_samples  = 0;')
                continue

            # Change train() signature to accept KList* params
            if f'static void {name}_train()' in line:
                in_train = True
                new_lines.append(f'static void {name}_train(KList* {inputs_var}_arg, KList* {targets_var}_arg) {{')
                continue

            if in_train and not injected and 'const int n  =' in line:
                # inject dynamic data unpacking
                new_lines.append(f'    int _dyn_n = (int){inputs_var}_arg->len;')
                new_lines.append(f'    {name}_n_samples = _dyn_n;')
                new_lines.append(f'    double* _dyn_inp = malloc(sizeof(double) * _dyn_n * {n_in});')
                new_lines.append(f'    double* _dyn_tgt = malloc(sizeof(double) * _dyn_n * {n_out});')
                new_lines.append(f'    for(int _si=0; _si<_dyn_n; _si++) {{')
                new_lines.append(f'        KList* _row_in  = kuda_list_grab_ptr({inputs_var}_arg, _si);')
                new_lines.append(f'        KList* _row_tgt = kuda_list_grab_ptr({targets_var}_arg, _si);')
                new_lines.append(f'        if(_row_in)  for(int _fi=0;_fi<{n_in}; _fi++) _dyn_inp[_si*{n_in} +_fi]=kuda_list_grab(_row_in, _fi);')
                new_lines.append(f'        if(_row_tgt) for(int _fo=0;_fo<{n_out};_fo++) _dyn_tgt[_si*{n_out}+_fo]=kuda_list_grab(_row_tgt,_fo);')
                new_lines.append(f'    }}')
                new_lines.append(f'    const int n = _dyn_n;')
                new_lines.append(f'    const int ni = {n_in};')
                new_lines.append(f'    const int no = {n_out};')
                injected = True
                # skip the original "const int n  = ..." line
                continue

            if in_train and injected:
                # skip duplicate ni/no declarations
                if ('const int ni =' in line or 'const int no =' in line or
                        'const int n  =' in line):
                    continue
                # redirect static array refs to dynamic ones
                line = line.replace(f'{name}_data_in  +', '_dyn_inp +')
                line = line.replace(f'{name}_data_tgt +', '_dyn_tgt +')
                line = line.replace(f'{name}_data_in +',  '_dyn_inp +')

            new_lines.append(line)

        # Fix call site: mynet_train() -> mynet_train(inputs, targets)
        patched = []
        for line in new_lines:
            stripped = line.strip()
            if stripped == f'{name}_train();':
                indent = line[:len(line) - len(line.lstrip())]
                line = f'{indent}{name}_train({inputs_var}, {targets_var});'
            patched.append(line)

        return patched

    def _gen_net_load_decl(self, node):
        """Generate C declarations for ~name = net.load("file.json").
        Reads the JSON at codegen time to know architecture,
        then emits a _load() function that reads weights at runtime."""
        import json as _json
        from interpreter import Interpreter as _Interp
        interp = _Interp()
        path = interp.eval(node.path_node, interp.global_env)

        try:
            with open(path) as _f:
                data = _json.load(_f)
        except FileNotFoundError:
            raise CompileError(f"net.load: plik '{path}' nie istnieje (potrzebny przy kompilacji)", getattr(node, 'line', None))

        layers   = data['layers']
        act_name = data.get('act', 'tanh')
        out_name = data.get('act_out', act_name)

        name  = node.name
        NAME  = name.upper()
        n_layers  = len(layers)
        max_layer = max(layers)
        n_weights = sum(layers[i]*layers[i+1] for i in range(n_layers-1))
        n_biases  = sum(layers[i+1]           for i in range(n_layers-1))
        n_inputs  = layers[0]
        n_outputs = layers[-1]

        act_c = {
            'tanh':    ('kuda_tanh_act', 'kuda_tanh_d'),
            'sigmoid': ('kuda_sigmoid',  'kuda_sigmoid_d'),
            'relu':    ('kuda_relu',      'kuda_relu_d'),
            'leaky':   ('kuda_leaky',     'kuda_leaky_d'),
            'linear':  ('kuda_linear_act','kuda_linear_d'),
        }
        af, af_d = act_c.get(act_name, ('kuda_tanh_act', 'kuda_tanh_d'))
        of, of_d = act_c.get(out_name, (af, af_d))

        L = []
        L.append(f'/* net.load: {name} from {path} */')
        L.append(f'static int    {name}_layers[]   = {{{", ".join(str(l) for l in layers)}}};')
        L.append(f'static double {name}_W[{n_weights}];')
        L.append(f'static double {name}_B[{n_biases}];')
        L.append(f'static int    {name}_n_inputs   = {n_inputs};')
        L.append(f'static int    {name}_n_outputs  = {n_outputs};')
        L.append(f'static int    {name}_n_samples  = 0;')
        L.append('')

        # activation wrappers
        L.append(f'static double {name}_act_fn(double x, int is_last) {{')
        if af == of:
            L.append(f'    (void)is_last; return {af}(x);')
        else:
            L.append(f'    return is_last ? {of}(x) : {af}(x);')
        L.append('}')
        L.append(f'static double {name}_act_d_fn(double x, int is_last) {{')
        if af_d == of_d:
            L.append(f'    (void)is_last; return {af_d}(x);')
        else:
            L.append(f'    return is_last ? {of_d}(x) : {af_d}(x);')
        L.append('}')
        L.append('')

        L.append(f'#define {NAME}_MAX_LAYER {max_layer}')
        L.append(f'#define {NAME}_N_LAYERS  {n_layers}')
        L.append('')

        # forward pass (same as gen_net_c)
        L.append(f'static void {name}_forward(double* input, double acts[][{NAME}_MAX_LAYER]) {{')
        L.append(f'    for(int j=0; j<{name}_layers[0]; j++) acts[0][j] = input[j];')
        L.append(f'    int w_off=0;')
        L.append(f'    for(int li=0; li<{NAME}_N_LAYERS-1; li++) {{')
        L.append(f'        int ni={name}_layers[li], no={name}_layers[li+1];')
        L.append(f'        int is_last=(li=={NAME}_N_LAYERS-2);')
        L.append(f'        for(int j=0; j<no; j++) {{')
        L.append(f'            double z={name}_B[/*b_off*/0];')  # placeholder — fix below
        L.append(f'            int b_off=0; for(int _l=0;_l<li;_l++) b_off+={name}_layers[_l+1];')
        L.append(f'            z={name}_B[b_off+j];')
        L.append(f'            for(int k=0; k<ni; k++) z += acts[li][k] * {name}_W[w_off + j*ni + k];')
        L.append(f'            acts[li+1][j] = {name}_act_fn(z, is_last);')
        L.append(f'        }}')
        L.append(f'        w_off += ni*no;')
        L.append(f'    }}')
        L.append(f'}}')
        L.append('')

        # predict
        L.append(f'static double {name}_predict(double* input) {{')
        L.append(f'    double acts[{NAME}_N_LAYERS][{NAME}_MAX_LAYER];')
        L.append(f'    {name}_forward(input, acts);')
        L.append(f'    return acts[{NAME}_N_LAYERS-1][0];')
        L.append(f'}}')
        L.append('')

        # load function — reads weights from file at runtime
        L.append(f'static void {name}_load() {{')
        L.append(f'    FILE* f = fopen("{path}", "r");')
        L.append(f'    if(!f) {{ printf("net.load: nie mozna otworzyc {path}\\n"); return; }}')
        L.append(f'    int wi=0, bi=0, in_w=0, in_b=0, c;')
        L.append(f'    while((c=fgetc(f))!=EOF) {{')
        L.append(f'        if(c==\'W\' && !in_w && !in_b) {{ fgetc(f);fgetc(f);fgetc(f); in_w=1; }}')
        L.append(f'        else if(c==\'B\' && wi>={n_weights} && !in_b) {{ fgetc(f);fgetc(f);fgetc(f); in_b=1; in_w=0; }}')
        L.append(f'        else if(in_w && (c==\'-\'||(c>=\'0\'&&c<=\'9\'))) {{')
        L.append(f'            ungetc(c,f); double v; fscanf(f,"%lf",&v);')
        L.append(f'            if(wi<{n_weights}) {name}_W[wi++]=v;')
        L.append(f'        }} else if(in_b && (c==\'-\'||(c>=\'0\'&&c<=\'9\'))) {{')
        L.append(f'            ungetc(c,f); double v; fscanf(f,"%lf",&v);')
        L.append(f'            if(bi<{n_biases}) {name}_B[bi++]=v;')
        L.append(f'        }}')
        L.append(f'    }}')
        L.append(f'    fclose(f);')
        L.append(f'    printf("Wagi wczytane z {path}\\n");')
        L.append(f'}}')
        L.append('')

        ninfo = {
            'layers':   layers,
            'n_inputs': n_inputs,
            'n_outputs':n_outputs,
        }
        return L, ninfo


        """
        Generate a C struct + constructor + methods for a Kuda model.
        
        model Hero:
            fun init(self, name):
                self.hp = 100
        
        Becomes:
            typedef struct { double hp; char* name; ... } Hero;
            Hero* Hero_new(...) { ... }
            double Hero_method(Hero* self, ...) { ... }
        """
        name = node.name
        
        # First pass: find all self.x assignments to discover fields
        fields = {}  # field_name -> type
        for stmt in node.body:
            if isinstance(stmt, FunNode):
                self._scan_model_fields(stmt.body, fields)
        
        self.models[name] = fields
        
        lines = []
        
        # Generate struct
        lines.append(f'/* Model: {name} */')
        lines.append(f'typedef struct {{')
        for fname, ftype in fields.items():
            if ftype == 'str':    lines.append(f'    char* {fname};')
            elif ftype == 'bool': lines.append(f'    int {fname};')
            elif ftype == 'list': lines.append(f'    KList* {fname};')
            else:                 lines.append(f'    double {fname};')
        lines.append(f'}} {name};')
        lines.append('')
        
        # Generate constructor (calls init)
        init_fun = None
        for stmt in node.body:
            if isinstance(stmt, FunNode) and stmt.name == 'init':
                init_fun = stmt
                break
        
        if init_fun:
            params_no_self = [p for p in init_fun.params if p != 'self']
            # Figure out param types from init body
            param_types = self._guess_param_types(init_fun.body, params_no_self)
            c_params = ', '.join(f'{param_types.get(p, "double")} {p}' for p in params_no_self)
            lines.append(f'{name}* {name}_new({c_params}) {{')
            lines.append(f'    {name}* self = malloc(sizeof({name}));')
            # Zero init all fields
            for fname, ftype in fields.items():
                if ftype == 'str':    lines.append(f'    self->{fname} = "";')
                elif ftype == 'bool': lines.append(f'    self->{fname} = 0;')
                elif ftype == 'list': lines.append(f'    self->{fname} = NULL;')
                else:                 lines.append(f'    self->{fname} = 0;')
            
            # Generate init body
            old_lines, old_indent, old_vars = self.lines, self.indent, dict(self.vars)
            self.lines = []; self.indent = 1
            self.vars = {p: param_types.get(p, 'double') for p in params_no_self}
            self.vars['self'] = name
            self.vars['_self_model'] = name
            for stmt in init_fun.body:
                self._gen_model_stmt(stmt, name)
            lines.extend(self.lines)
            self.lines, self.indent, self.vars = old_lines, old_indent, old_vars
            
            lines.append('    return self;')
            lines.append('}')
            lines.append('')
        
        # Generate methods
        for stmt in node.body:
            if isinstance(stmt, FunNode) and stmt.name != 'init':
                method_lines = self._gen_model_method(stmt, name, fields)
                lines.extend(method_lines)
                lines.append('')
        
        return lines

    def _scan_model_fields(self, stmts, fields):
        """Find all self.x = ... assignments to build field list."""
        STRING_FIELD_HINTS = {'name', 'ename', 'title', 'label', 'text', 'msg', 'description', 'type', 'kind', 'tag'}
        for node in stmts:
            if isinstance(node, AssignNode) and isinstance(node.name, AttrNode):
                obj = node.name.obj
                attr = node.name.attr
                if isinstance(obj, IdentNode) and obj.name == 'self':
                    if attr not in fields:
                        if isinstance(node.value, StringNode):
                            fields[attr] = 'str'
                        elif isinstance(node.value, IdentNode) and node.value.name in STRING_FIELD_HINTS:
                            fields[attr] = 'str'
                        elif attr in STRING_FIELD_HINTS:
                            fields[attr] = 'str'
                        elif isinstance(node.value, BoolNode):
                            fields[attr] = 'bool'
                        elif isinstance(node.value, ListNode):
                            fields[attr] = 'list'
                        else:
                            fields[attr] = 'double'
            if isinstance(node, IfNode):
                for _, body in node.cases:
                    self._scan_model_fields(body, fields)
                if node.else_body:
                    self._scan_model_fields(node.else_body, fields)
            if isinstance(node, RepeatNode): self._scan_model_fields(node.body, fields)
            if isinstance(node, EachNode):   self._scan_model_fields(node.body, fields)
            if isinstance(node, TilNode):    self._scan_model_fields(node.body, fields)

    def _guess_param_types(self, stmts, params):
        """Guess C types for parameters based on how they're assigned to fields."""
        STRING_FIELD_HINTS = {'name', 'ename', 'title', 'label', 'text', 'msg', 'description', 'type', 'kind', 'tag'}
        types = {p: 'double' for p in params}
        # If param name itself hints at a string
        for p in params:
            if p in STRING_FIELD_HINTS:
                types[p] = 'char*'
        # Check what fields they're assigned to
        for node in stmts:
            if isinstance(node, AssignNode) and isinstance(node.name, AttrNode):
                attr = node.name.attr
                if isinstance(node.value, IdentNode) and node.value.name in params:
                    p = node.value.name
                    if attr in STRING_FIELD_HINTS:
                        types[p] = 'char*'
        return types

    def _gen_model_stmt(self, node, model_name):
        """Generate statements inside a model method, handling self.x = ..."""
        if node is None: return
        if isinstance(node, AssignNode):
            if isinstance(node.name, AttrNode):
                obj = node.name.obj
                attr = node.name.attr
                if isinstance(obj, IdentNode) and obj.name == 'self':
                    val, typ = self._gen_expr(node.value)
                    self.emit(f'    self->{attr} = {val};')
                    return
            self._gen_assign(node)
        elif isinstance(node, OutNode):
            self._gen_out(node)
        elif isinstance(node, IfNode):
            self._gen_if_model(node, model_name)
        elif isinstance(node, GiveNode):
            val, typ = self._gen_expr(node.value)
            if typ == 'str' or typ in self.models:
                self.emit(f'return {val};')
            else:
                self.emit(f'return (double)({val});')
        else:
            self._gen_stmt(node)

    def _gen_if_model(self, node, model_name):
        first = True
        for cond, body in node.cases:
            cval, _ = self._gen_expr(cond)
            if first: self.emit(f'if ({cval}) {{'); first = False
            else:     self.emit(f'}} else if ({cval}) {{')
            self.indent += 1
            for s in body: self._gen_model_stmt(s, model_name)
            self.indent -= 1
        if node.else_body:
            self.emit('} else {')
            self.indent += 1
            for s in node.else_body: self._gen_model_stmt(s, model_name)
            self.indent -= 1
        self.emit('}')

    def _gen_model_method(self, fun_node, model_name, fields):
        """Generate a C function for a model method."""
        old_lines, old_indent, old_vars = self.lines, self.indent, dict(self.vars)
        self.lines = []; self.indent = 0
        
        params_no_self = [p for p in fun_node.params if p != 'self']
        ret_type = self._scan_return_type(fun_node.body)
        
        c_ret = 'char*' if ret_type == 'str' else 'double'
        params_str = f'{model_name}* self'
        if params_no_self:
            params_str += ', ' + ', '.join(f'double {p}' for p in params_no_self)
        
        self.emit(f'{c_ret} {model_name}_{fun_node.name}({params_str}) {{')
        self.indent += 1
        
        # Set up vars: self fields accessible, plus params
        self.vars = {p: 'double' for p in params_no_self}
        self.vars['self'] = model_name
        self.vars['_self_model'] = model_name
        
        # Pre-declare local variables
        pre = self._prescan_vars(fun_node.body, set(params_no_self) | {'self'})
        for vname, vtyp in pre.items():
            self.vars[vname] = vtyp
            if vtyp == 'str':    self.emit(f'char* {vname} = NULL;')
            elif vtyp == 'bool': self.emit(f'int {vname} = 0;')
            elif vtyp in ('list', 'strlist'): self.emit(f'KList* {vname} = NULL;')
            else:                self.emit(f'double {vname} = 0;')
        
        for stmt in fun_node.body:
            self._gen_model_stmt(stmt, model_name)
        
        if ret_type == 'str':
            self.emit('return "";')
        else:
            self.emit('return 0;')
        self.indent -= 1
        self.emit('}')
        
        result = self.lines
        self.lines, self.indent, self.vars = old_lines, old_indent, old_vars
        return result

    def _prescan_vars(self, stmts, known_params):
        """
        Pre-scan function body to find all assigned variables and their types.
        This lets us declare them all at the top of the C function, avoiding
        'undeclared variable' errors when variables are assigned inside if/loops.
        """
        found = {}
        STR_FUNCS = {'input', 'str', 'caps', 'small', 'trim', 'swap', 'merge', 'read', 'kuda_concat'}
        LIST_FUNCS2 = {'cut', 'softmax', 'xav', 'he', 'snip', 'pack', 'shuffle'}
        STRLIST_FUNCS2 = {'readlines'}

        def is_str_expr(node):
            """Rekurencyjnie sprawdź czy wyrażenie zwraca string."""
            if isinstance(node, StringNode): return True
            if isinstance(node, BinOpNode) and node.op == '+':
                return is_str_expr(node.left) or is_str_expr(node.right)
            if isinstance(node, CallNode) and isinstance(node.func, IdentNode):
                fname = node.func.name
                if fname in STR_FUNCS: return True
                if fname in getattr(self, 'func_return_types', {}) and self.func_return_types[fname] == 'str': return True
            if isinstance(node, IdentNode):
                return found.get(node.name) == 'str' or self.vars.get(node.name) == 'str'
            return False

        def is_list_expr(node):
            """Sprawdź czy wyrażenie zwraca listę."""
            if isinstance(node, (ListNode, ListCompNode)): return True
            if isinstance(node, BinOpNode) and node.op == '+':
                return is_list_expr(node.left) or is_list_expr(node.right)
            if isinstance(node, IdentNode):
                t = found.get(node.name) or self.vars.get(node.name)
                return t in ('list', 'strlist')
            if isinstance(node, CallNode) and isinstance(node.func, IdentNode):
                fname = node.func.name
                if fname in LIST_FUNCS2: return True
            return False

        def scan(stmts):
            for node in stmts:
                if isinstance(node, AssignNode) and isinstance(node.name, str):
                    if node.name not in known_params:
                        if isinstance(node.value, StringNode):
                            found[node.name] = 'str'
                        elif isinstance(node.value, BoolNode):
                            found[node.name] = 'bool'
                        elif isinstance(node.value, (ListNode, ListCompNode)):
                            if isinstance(node.value, ListNode):
                                has_str = any(isinstance(e, StringNode) for e in node.value.elements)
                                found[node.name] = 'strlist' if has_str else 'list'
                            else:
                                found[node.name] = 'list'
                        elif is_list_expr(node.value):
                            found[node.name] = 'list'
                        elif is_str_expr(node.value):
                            found[node.name] = 'str'
                        elif isinstance(node.value, CallNode):
                            if isinstance(node.value.func, IdentNode):
                                fname = node.value.func.name
                                if fname in self.models:
                                    found[node.name] = fname
                                elif fname in getattr(self, 'func_return_types', {}):
                                    ret = self.func_return_types[fname]
                                    found[node.name] = ret if ret != 'double' else 'double'
                                elif fname in LIST_FUNCS2:
                                    found[node.name] = 'list'
                                elif fname in STRLIST_FUNCS2:
                                    found[node.name] = 'strlist'
                                else:
                                    found.setdefault(node.name, 'double')
                            elif isinstance(node.value.func, AttrNode):
                                # obj.method() — check for net.predict() multi-output
                                attr_node = node.value.func
                                if (isinstance(attr_node.obj, IdentNode)
                                        and attr_node.attr == 'predict'
                                        and attr_node.obj.name in self._net_info):
                                    n_out = self._net_info[attr_node.obj.name].get('n_outputs', 1)
                                    found[node.name] = 'list' if n_out > 1 else 'double'
                                elif attr_node.attr == 'cut':
                                    found[node.name] = 'strlist'
                                else:
                                    found.setdefault(node.name, 'double')
                            else:
                                found.setdefault(node.name, 'double')
                        elif isinstance(node.value, AttrNode):
                            def _is_data_chain2(n):
                                if isinstance(n, IdentNode) and n.name == 'data': return True
                                if isinstance(n, AttrNode): return _is_data_chain2(n.obj)
                                if isinstance(n, CallNode): return _is_data_chain2(n.func)
                                return False
                            if _is_data_chain2(node.value):
                                found[node.name] = 'list'
                            else:
                                found.setdefault(node.name, 'double')
                        elif isinstance(node.value, IndexNode):
                            # str[idx] -> str, strlist[idx] -> str, list[idx] -> double
                            obj_node = node.value.obj
                            if isinstance(obj_node, IdentNode):
                                otyp = found.get(obj_node.name) or self.vars.get(obj_node.name, 'double')
                                if otyp in ('str', 'strlist'):
                                    found[node.name] = 'str'
                                else:
                                    found.setdefault(node.name, 'double')
                            else:
                                found.setdefault(node.name, 'double')
                        else:
                            found.setdefault(node.name, 'double')
                if isinstance(node, IfNode):
                    for _, body in node.cases:
                        scan(body)
                    if node.else_body:
                        scan(node.else_body)
                if isinstance(node, RepeatNode): scan(node.body)
                if isinstance(node, EachNode):   scan(node.body)
                if isinstance(node, TilNode):    scan(node.body)
        scan(stmts)
        return found

    def _gen_function(self, node):
        old_lines, old_indent, old_vars = self.lines, self.indent, dict(self.vars)
        self.lines = []; self.indent = 0
        if isinstance(node, FunNode):
            ret_type = self._scan_return_type(node.body)
            if ret_type == 'str':
                c_ret = 'char*'
                c_ret_default = 'return "";'
            elif ret_type in self.models:
                c_ret = f'{ret_type}*'
                c_ret_default = 'return NULL;'
            else:
                c_ret = 'double'
                c_ret_default = 'return 0;'

            # Use scanned param types if available
            scanned = getattr(self, 'func_param_types', {}).get(node.name, [])
            c_params = []
            param_var_types = {}
            for i, p in enumerate(node.params):
                if i < len(scanned) and scanned[i] in self.models:
                    c_params.append(f'{scanned[i]}* {p}')
                    param_var_types[p] = scanned[i]
                elif i < len(scanned) and scanned[i] == 'str':
                    c_params.append(f'char* {p}')
                    param_var_types[p] = 'str'
                else:
                    c_params.append(f'double {p}')
                    param_var_types[p] = 'double'

            self.emit(f'{c_ret} {"kuda_main" if node.name == "main" else node.name}({", ".join(c_params)}) {{')
            self.indent += 1
            for p, pt in param_var_types.items():
                self.vars[p] = pt
            pre = self._prescan_vars(node.body, set(node.params))
            for vname, vtyp in pre.items():
                self.vars[vname] = vtyp
                if vtyp == 'str':          self.emit(f'char* {vname} = NULL;')
                elif vtyp == 'bool':       self.emit(f'int {vname} = 0;')
                elif vtyp in ('list', 'strlist'):  self.emit(f'KList* {vname} = NULL;')
                elif vtyp in self.models:  self.emit(f'{vtyp}* {vname} = NULL;')
                else:                      self.emit(f'double {vname} = 0;')
            for stmt in node.body:
                self._gen_stmt(stmt)
            self.emit(c_ret_default)
            self.indent -= 1
            self.emit('}')
        result = self.lines
        self.lines, self.indent, self.vars = old_lines, old_indent, old_vars
        return result

    def _scan_return_type(self, stmts):
        """Check if any give statement returns a string or model pointer."""
        for node in stmts:
            if isinstance(node, GiveNode):
                if isinstance(node.value, StringNode):
                    return 'str'
                if isinstance(node.value, CallNode) and isinstance(node.value.func, IdentNode):
                    if node.value.func.name in self.models:
                        return node.value.func.name  # returns model type
            if isinstance(node, IfNode):
                for _, body in node.cases:
                    t = self._scan_return_type(body)
                    if t != 'double': return t
                if node.else_body:
                    t = self._scan_return_type(node.else_body)
                    if t != 'double': return t
            if isinstance(node, RepeatNode):
                t = self._scan_return_type(node.body)
                if t != 'double': return t
            if isinstance(node, EachNode):
                t = self._scan_return_type(node.body)
                if t != 'double': return t
            if isinstance(node, TilNode):
                t = self._scan_return_type(node.body)
                if t != 'double': return t
        return 'double'

    def _gen_stmt(self, node):
        if node is None: return
        if isinstance(node, NetNode):
            dyn = getattr(self, '_dynamic_nets', {}).get(node.name)
            if dyn:
                iv, tv = dyn
                self.emit(f'{node.name}_train({iv}, {tv});')
            else:
                self.emit(f'{node.name}_train();')
            return
        if isinstance(node, NetLoadNode):
            # runtime load: call the generated _load() function
            self.emit(f'{node.name}_load();')
            return
        if isinstance(node, AssignNode): self._gen_assign(node)
        elif isinstance(node, AugAssignNode):
            val, _ = self._gen_expr(node.value)
            op_map = {'+': '+=', '-': '-=', '*': '*=', '/': '/='}
            cop = op_map.get(node.op, node.op)
            self.emit(f'{node.name} {cop} {val};')
        elif isinstance(node, IndexAssignNode):
            obj, otyp = self._gen_expr(node.target.obj)
            idx, _ = self._gen_expr(node.target.index)
            val, vtyp = self._gen_expr(node.value)
            if otyp in ('list', 'strlist'):
                if vtyp == 'str':
                    self.emit(f'{obj}->data[(int)({idx})] = (double)(intptr_t)({val});')
                else:
                    self.emit(f'{obj}->data[(int)({idx})] = {val};')
            else:
                self.emit(f'{obj}[(int)({idx})] = {val};')
        elif isinstance(node, OutNode): self._gen_out(node)
        elif isinstance(node, IfNode): self._gen_if(node)
        elif isinstance(node, RepeatNode): self._gen_repeat(node)
        elif isinstance(node, EachNode): self._gen_each(node)
        elif isinstance(node, TilNode): self._gen_til(node)
        elif isinstance(node, FunNode): pass
        elif isinstance(node, GiveNode):
            val, typ = self._gen_expr(node.value)
            if typ == 'str' or typ in self.models:
                self.emit(f'return {val};')
            else:
                self.emit(f'return (double)({val});')
        elif isinstance(node, TryNode):
            for s in node.try_body: self._gen_stmt(s)
        elif isinstance(node, CheckNode):
            self._gen_check(node)
        elif isinstance(node, BreakNode): self.emit('break;')
        elif isinstance(node, ContinueNode): self.emit('continue;')
        elif isinstance(node, ExternNode):
            # extern "plik.c" — dołącz plik C do kompilacji
            if node.c_file is not None:
                if node.c_file not in self.extra_c_files:
                    self.extra_c_files.append(node.c_file)
                return
            # extern typ nazwa(params) — deklaracja funkcji
            c_ret = {'double': 'double', 'str': 'char*', 'void': 'void', 'int': 'double'}.get(node.ret_type, 'double')
            c_params = []
            for pname, ptype in node.params:
                c_ptype = {'double': 'double', 'str': 'char*', 'void': 'void', 'int': 'int'}.get(ptype, 'double')
                c_params.append(f'{c_ptype} {pname}')
            params_str = ', '.join(c_params) if c_params else 'void'
            self.extern_decls.append(f'extern {c_ret} {node.name}({params_str});')
            self.extern_funcs[node.name] = node.ret_type
        elif isinstance(node, UseNode):
            # C library: use sdl2, use gl, etc.
            if node.module and node.filepath is None:
                flags = self.C_LIBS.get(node.module)
                if flags:
                    for f in flags:
                        if f not in self.link_flags:
                            self.link_flags.append(f)
                # Python modules are silently ignored in C mode
        else:
            try:
                val, _ = self._gen_expr(node)
                self.emit(f'{val};')
            except: pass

    def _gen_assign(self, node):
        # Skip data.cust = ... — it's only meaningful for DataBuilder setup, not C
        if isinstance(node.name, AttrNode):
            obj = node.name.obj
            if isinstance(obj, IdentNode) and obj.name == 'data' and node.name.attr == 'cust':
                return
        if isinstance(node.name, str):
            val, typ = self._gen_expr(node.value)
            if node.name not in self.vars:
                self.vars[node.name] = typ
                if typ == 'str':          self.emit(f'char* {node.name} = {val};')
                elif typ == 'bool':       self.emit(f'int {node.name} = {val};')
                elif typ == 'matrix':     self.emit(f'KMatrix* {node.name} = {val};')
                elif typ in ('list', 'strlist'): self.emit(f'KList* {node.name} = {val};')
                elif typ in self.models:  self.emit(f'{typ}* {node.name} = {val};')
                else:                     self.emit(f'double {node.name} = {val};')
            else:
                self.emit(f'{node.name} = {val};')
        elif isinstance(node.name, AttrNode):
            obj = node.name.obj
            attr = node.name.attr
            val, vtyp = self._gen_expr(node.value)
            # self.field = ... inside model method
            if isinstance(obj, IdentNode) and obj.name == 'self':
                self.emit(f'self->{attr} = {val};')
                return
            obj_val, obj_typ = self._gen_expr(obj)
            # instance.field = ...
            if obj_typ in self.models:
                self.emit(f'{obj_val}->{attr} = {val};')
                return
            self.emit(f'{obj_val}.{attr} = {val};')

    def _gen_out(self, node):
        val, typ = self._gen_expr(node.value)
        if typ == 'str':    self.emit(f'kuda_print_str({val});')
        elif typ in ('list', 'strlist'): self.emit(f'kuda_print_list({val});')
        elif typ == 'bool': self.emit(f'kuda_print_bool({val});')
        elif typ == 'matrix': self.emit(f'kuda_mat_print({val});')
        else:               self.emit(f'kuda_print_double({val});')

    def _gen_if(self, node):
        first = True
        for cond, body in node.cases:
            cval, _ = self._gen_expr(cond)
            if first: self.emit(f'if ({cval}) {{'); first = False
            else:     self.emit(f'}} else if ({cval}) {{')
            self.indent += 1
            for s in body: self._gen_stmt(s)
            self.indent -= 1
        if node.else_body:
            self.emit('} else {')
            self.indent += 1
            for s in node.else_body: self._gen_stmt(s)
            self.indent -= 1
        self.emit('}')

    def _gen_check(self, node):
        """Generuje check/is jako serię if/else if w C."""
        expr_val, expr_typ = self._gen_expr(node.expr)
        # Zachowaj wartość w tymczasowej zmiennej żeby nie ewaluować wielokrotnie
        tmp = self.fresh_tmp()
        if expr_typ == 'str':
            self.emit(f'char* {tmp} = {expr_val};')
        else:
            self.emit(f'double {tmp} = {expr_val};')

        first = True
        for case_val, body in node.cases:
            cv, ct = self._gen_expr(case_val)
            # Porównanie — stringi przez strcmp, liczby przez ==
            if expr_typ == 'str' or ct == 'str':
                cond = f'strcmp({tmp}, {cv}) == 0'
            else:
                cond = f'{tmp} == {cv}'

            if first:
                self.emit(f'if ({cond}) {{')
                first = False
            else:
                self.emit(f'}} else if ({cond}) {{')
            self.indent += 1
            for s in body:
                self._gen_stmt(s)
            self.indent -= 1

        if node.else_body:
            if first:
                self.emit('{')  # tylko other bez żadnego is
            else:
                self.emit('} else {')
            self.indent += 1
            for s in node.else_body:
                self._gen_stmt(s)
            self.indent -= 1

        if not first or node.else_body:
            self.emit('}')

    def _gen_repeat(self, node):
        count, _ = self._gen_expr(node.count)
        tmp = self.fresh_tmp()
        self.emit(f'for (int {tmp} = 0; {tmp} < (int)({count}); {tmp}++) {{')
        self.indent += 1
        for s in node.body: self._gen_stmt(s)
        self.indent -= 1
        self.emit('}')

    def _gen_each(self, node):
        if isinstance(node.iterable, CallNode) and isinstance(node.iterable.func, IdentNode):
            if node.iterable.func.name == 'range':
                args = node.iterable.args
                self.vars[node.var] = 'double'
                if len(args) == 1:
                    end, _ = self._gen_expr(args[0])
                    self.emit(f'for (double {node.var} = 0; {node.var} < {end}; {node.var}++) {{')
                elif len(args) == 2:
                    start, _ = self._gen_expr(args[0]); end, _ = self._gen_expr(args[1])
                    self.emit(f'for (double {node.var} = {start}; {node.var} < {end}; {node.var}++) {{')
                elif len(args) == 3:
                    start, _ = self._gen_expr(args[0])
                    end,   _ = self._gen_expr(args[1])
                    step,  _ = self._gen_expr(args[2])
                    self.emit(f'for (double {node.var} = {start}; {node.var} < {end}; {node.var} += {step}) {{')
                else:
                    self.emit(f'/* range(): unsupported arg count */')
                    return
                self.indent += 1
                for s in node.body: self._gen_stmt(s)
                self.indent -= 1
                self.emit('}')
                return

        # each x in lista — iteracja po KList
        iterable, ityp = self._gen_expr(node.iterable)
        if ityp == 'strlist':
            tmp_i = self.fresh_tmp()
            self.vars[node.var] = 'str'
            self.emit(f'for (int {tmp_i} = 0; {tmp_i} < {iterable}->len; {tmp_i}++) {{')
            self.indent += 1
            self.emit(f'char* {node.var} = (char*)(intptr_t){iterable}->data[{tmp_i}];')
            for s in node.body: self._gen_stmt(s)
            self.indent -= 1
            self.emit('}')
        elif ityp == 'list':
            tmp_i = self.fresh_tmp()
            self.vars[node.var] = 'double'
            self.emit(f'for (int {tmp_i} = 0; {tmp_i} < {iterable}->len; {tmp_i}++) {{')
            self.indent += 1
            self.emit(f'double {node.var} = {iterable}->data[{tmp_i}];')
            for s in node.body: self._gen_stmt(s)
            self.indent -= 1
            self.emit('}')
        else:
            # fallback — nie znany typ
            self.emit(f'/* each: nieznany typ iteracji dla {iterable} */')

    def _gen_til(self, node):
        cval, _ = self._gen_expr(node.condition)
        self.emit(f'while ({cval}) {{')
        self.indent += 1
        for s in node.body: self._gen_stmt(s)
        self.indent -= 1
        self.emit('}')

    def _gen_expr(self, node):
        if isinstance(node, NumberNode): return str(float(node.value)), 'double'
        if isinstance(node, StringNode):
            e = node.value.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')
            return f'"{e}"', 'str'
        if isinstance(node, BoolNode): return ('1' if node.value else '0'), 'bool'
        if isinstance(node, NoneNode): return '0', 'double'
        if isinstance(node, ListCompNode):
            # [expr each var in iterable]
            tmp = self.fresh_tmp()
            self.emit(f'KList* {tmp} = kuda_list_new();')
            # Save and set loop var type
            old_typ = self.vars.get(node.var)
            self.vars[node.var] = 'double'
            iterable, ityp = self._gen_expr(node.iterable)
            if isinstance(node.iterable, CallNode) and isinstance(node.iterable.func, IdentNode) and node.iterable.func.name == 'range':
                args = node.iterable.args
                if len(args) == 1:
                    end, _ = self._gen_expr(args[0])
                    self.emit(f'for (double {node.var} = 0; {node.var} < {end}; {node.var}++) {{')
                else:
                    start, _ = self._gen_expr(args[0]); end, _ = self._gen_expr(args[1])
                    self.emit(f'for (double {node.var} = {start}; {node.var} < {end}; {node.var}++) {{')
            else:
                tmp_i = self.fresh_tmp()
                self.emit(f'for (int {tmp_i} = 0; {tmp_i} < {iterable}->len; {tmp_i}++) {{')
                self.emit(f'    double {node.var} = {iterable}->data[{tmp_i}];')
            self.indent += 1
            val, _ = self._gen_expr(node.expr)
            self.emit(f'kuda_list_add({tmp}, {val});')
            self.indent -= 1
            self.emit('}')
            if old_typ is None: self.vars.pop(node.var, None)
            else: self.vars[node.var] = old_typ
            return tmp, 'list'

        if isinstance(node, ListNode):
            # Create a new list and add all elements
            tmp = self.fresh_tmp()
            self.emit(f'KList* {tmp} = kuda_list_new();')
            is_strlist = False
            for elem in node.elements:
                val, typ = self._gen_expr(elem)
                if typ == 'str':
                    is_strlist = True
                    self.emit(f'kuda_list_add({tmp}, (double)(intptr_t)({val}));')
                else:
                    self.emit(f'kuda_list_add({tmp}, {val});')
            return tmp, 'strlist' if is_strlist else 'list'
        if isinstance(node, IdentNode):
            if node.name == 'pi': return 'M_PI', 'double'
            if node.name == 'True': return '1', 'bool'
            if node.name == 'False': return '0', 'bool'
            return node.name, self.vars.get(node.name, 'double')
        if isinstance(node, BinOpNode): return self._gen_binop(node)
        if isinstance(node, UnaryOpNode):
            val, typ = self._gen_expr(node.operand)
            if node.op == '-': return f'(-{val})', typ
            if node.op == 'not': return f'(!{val})', 'bool'
        if isinstance(node, CallNode): return self._gen_call(node)
        if isinstance(node, AttrNode): return self._gen_attr_access(node)
        if isinstance(node, IndexNode):
            obj, otyp = self._gen_expr(node.obj)
            idx, _ = self._gen_expr(node.index)
            if otyp == 'strlist':
                return f'((char*)(intptr_t)kuda_list_grab({obj}, (int)({idx})))', 'str'
            if otyp == 'list':
                return f'kuda_list_grab({obj}, (int)({idx}))', 'double'
            if otyp == 'str':
                # str[i] -> single char as heap-allocated string
                tmp = self._tmp_var()
                self.emit(f'char {tmp}_ch[2]; {tmp}_ch[0] = {obj}[(int)({idx})]; {tmp}_ch[1] = 0;')
                self.emit(f'char* {tmp}_s = strdup({tmp}_ch);')
                return f'{tmp}_s', 'str'
            return f'{obj}[(int)({idx})]', 'double'
        return '0', 'double'

    def _gen_binop(self, node):
        lval, ltyp = self._gen_expr(node.left)
        rval, rtyp = self._gen_expr(node.right)
        op = node.op
        if op == 'and': return f'({lval} && {rval})', 'bool'
        if op == 'or':  return f'({lval} || {rval})', 'bool'
        if op == '+' and (ltyp == 'str' or rtyp == 'str'):
            if ltyp != 'str': lval = f'kuda_double_to_str({lval})'
            if rtyp != 'str': rval = f'kuda_double_to_str({rval})'
            return f'kuda_concat({lval}, {rval})', 'str'
        if op == '+' and ltyp in ('list', 'strlist') and rtyp in ('list', 'strlist'):
            return f'kuda_list_concat({lval}, {rval})', 'list'
        # String comparison using strcmp
        if ltyp == 'str' or rtyp == 'str':
            if op == '==': return f'(strcmp({lval}, {rval}) == 0)', 'bool'
            if op == '!=': return f'(strcmp({lval}, {rval}) != 0)', 'bool'
            if op == '<':  return f'(strcmp({lval}, {rval}) < 0)', 'bool'
            if op == '>':  return f'(strcmp({lval}, {rval}) > 0)', 'bool'
        if ltyp == 'matrix' or rtyp == 'matrix':
            if op == '+': return f'kuda_mat_add({lval}, {rval})', 'matrix'
            if op == '-': return f'kuda_mat_sub({lval}, {rval})', 'matrix'
            if op == '*':
                if ltyp == 'matrix' and rtyp == 'matrix': return f'kuda_mat_mul({lval}, {rval})', 'matrix'
                if ltyp == 'matrix': return f'kuda_mat_scale({lval}, {rval})', 'matrix'
                return f'kuda_mat_scale({rval}, {lval})', 'matrix'
        if op == '%': return f'((double)((long long)({lval}) % (long long)({rval})))', 'double'
        typ = 'bool' if op in ('==','!=','<','>','<=','>=') else 'double'
        return f'({lval} {op} {rval})', typ

    def _gen_attr_access(self, node):
        obj_val, obj_typ = self._gen_expr(node.obj)
        attr = node.attr
        if obj_typ == 'matrix':
            if attr == 'rows': return f'((double){obj_val}->rows)', 'double'
            if attr == 'cols': return f'((double){obj_val}->cols)', 'double'
        # self.field inside a model method
        if obj_val == 'self' and '_self_model' in self.vars:
            model_name = self.vars['_self_model']
            fields = self.models.get(model_name, {})
            ftype = fields.get(attr, 'double')
            return f'self->{attr}', ftype
        # instance.field (e.g. hero.hp)
        if obj_typ in self.models:
            fields = self.models.get(obj_typ, {})
            ftype = fields.get(attr, 'double')
            return f'{obj_val}->{attr}', ftype
        return f'{obj_val}', 'double'

    def _gen_call(self, node):
        if isinstance(node.func, AttrNode):
            return self._gen_method_call(node.func, node.args)
        if not isinstance(node.func, IdentNode):
            return '0', 'double'
        name = node.func.name
        args_eval = [self._gen_expr(a) for a in node.args]

        if name == 'out':
            val, typ = args_eval[0] if args_eval else ('""', 'str')
            if typ == 'str':    self.emit(f'kuda_print_str({val});')
            elif typ == 'list':   self.emit(f'kuda_print_list({val});')
            elif typ == 'matrix': self.emit(f'kuda_mat_print({val});')
            elif typ == 'bool': self.emit(f'kuda_print_bool({val});')
            else:               self.emit(f'kuda_print_double({val});')
            return '0', 'double'

        if name == 'str':
            val, typ = args_eval[0]
            if typ == 'str': return val, 'str'
            if typ in ('list', 'strlist'): return f'kuda_list_to_str({val})', 'str'
            return f'kuda_double_to_str({val})', 'str'
        if name == 'int':
            val, typ = args_eval[0]
            if typ == 'str': return f'((double)atoi({val}))', 'double'
            return f'((double)(long long)({val}))', 'double'
        if name == 'float':
            val, typ = args_eval[0]
            if typ == 'str': return f'((double)atof({val}))', 'double'
            return f'((double)({val}))', 'double'
        if name == 'abs':   val, _ = args_eval[0]; return f'fabs({val})', 'double'
        if name == 'round':
            val, _ = args_eval[0]
            if len(args_eval) == 1:
                return f'(double)(long long)round({val})', 'double'
            else:
                prec, _ = args_eval[1]
                return f'(round({val} * pow(10, {prec})) / pow(10, {prec}))', 'double'
        if name == 'exp':   val, _ = args_eval[0]; return f'exp({val})', 'double'
        if name == 'log':   val, _ = args_eval[0]; return f'log({val})', 'double'
        if name == 'prw':   val, _ = args_eval[0]; return f'sqrt({val})', 'double'
        if name == 'dwn':   val, _ = args_eval[0]; return f'floor({val})', 'double'
        if name == 'up':    val, _ = args_eval[0]; return f'ceil({val})', 'double'
        if name == 'pot':   b,_ = args_eval[0]; e,_ = args_eval[1]; return f'pow({b},{e})', 'double'
        if name == 'max' and len(args_eval)==2: a,_=args_eval[0];b,_=args_eval[1]; return f'fmax({a},{b})', 'double'
        if name == 'min' and len(args_eval)==2: a,_=args_eval[0];b,_=args_eval[1]; return f'fmin({a},{b})', 'double'
        # AI - activation functions
        if name == 'sigmoid':  val,_=args_eval[0]; return f'kuda_sigmoid({val})', 'double'
        if name == 'sigmoid_d':val,_=args_eval[0]; return f'kuda_sigmoid_d({val})', 'double'
        if name == 'tanh':     val,_=args_eval[0]; return f'kuda_tanh_act({val})', 'double'
        if name == 'tanh_d':   val,_=args_eval[0]; return f'kuda_tanh_d({val})', 'double'
        if name == 'relu':     val,_=args_eval[0]; return f'kuda_relu({val})', 'double'
        if name == 'relu_d':   val,_=args_eval[0]; return f'kuda_relu_d({val})', 'double'
        if name == 'leaky':    val,_=args_eval[0]; return f'kuda_leaky({val})', 'double'
        if name == 'leaky_d':  val,_=args_eval[0]; return f'kuda_leaky_d({val})', 'double'
        if name == 'clip':     val,_=args_eval[0];lo,_=args_eval[1];hi,_=args_eval[2]; return f'kuda_clip({val},{lo},{hi})', 'double'
        # AI - list operations
        if name == 'dot':      a,_=args_eval[0];b,_=args_eval[1]; return f'kuda_dot({a},{b})', 'double'
        if name == 'argmax':   val,_=args_eval[0]; return f'kuda_argmax({val})', 'double'
        if name == 'argmin':   val,_=args_eval[0]; return f'kuda_argmin({val})', 'double'
        if name == 'mean':     val,_=args_eval[0]; return f'kuda_mean({val})', 'double'
        if name == 'norm':     val,_=args_eval[0]; return f'kuda_norm({val})', 'double'
        if name == 'softmax':  val,_=args_eval[0]; return f'kuda_softmax({val})', 'list'
        if name == 'xav':      a,_=args_eval[0];b,_=args_eval[1]; return f'kuda_xav((int)({a}),(int)({b}))', 'list'
        if name == 'he':       a,_=args_eval[0]; return f'kuda_he((int)({a}))', 'list'
        if name == 'acc':      a,_=args_eval[0];b,_=args_eval[1]; return f'kuda_acc({a},{b})', 'double'
        if name == 'crent':    a,_=args_eval[0];b,_=args_eval[1]; return f'kuda_crent({a},{b})', 'double'
        if name == 'snip':     l,_=args_eval[0];s,_=args_eval[1];e,_=args_eval[2]; return f'kuda_snip({l},(int)({s}),(int)({e}))', 'list'
        if name == 'rand':       lo,_=args_eval[0];hi,_=args_eval[1]; return f'((double)kuda_rand((int)({lo}),(int)({hi})))', 'double'
        if name == 'rand_float': return 'kuda_rand_float()', 'double'
        if name == 'rand_normal':
            m,_=args_eval[0]; s,_=args_eval[1]
            return f'kuda_rand_normal({m},{s})', 'double'
        if name == 'shuffle':
            l,_=args_eval[0]
            self.emit(f'kuda_shuffle({l});')
            return '0', 'double'
        if name == 'wait':       val,_=args_eval[0]; return f'sleep((int)({val}))', 'double'
        if name == 'time':       return '((double)clock()/CLOCKS_PER_SEC)', 'double'
        if name == 'input':      p = args_eval[0][0] if args_eval else '""'; return f'kuda_input({p})', 'str'
        
        # String functions
        if name == 'len':
            val,typ=args_eval[0]
            if typ=='str': return f'((double)strlen({val}))', 'double'
            if typ in ('list','strlist'): return f'((double){val}->len)', 'double'
            return '0', 'double'
        if name == 'sum':
            val,typ=args_eval[0]
            if typ in ('list','strlist'): return f'kuda_list_sum({val})', 'double'
            return '0', 'double'
        if name == 'cut':
            s,_=args_eval[0]
            d = args_eval[1][0] if len(args_eval) > 1 else '" "'
            return f'kuda_cut({s}, {d})', 'list'
        if name == 'swap' and len(args_eval)==3:
            s,_=args_eval[0]; f,_=args_eval[1]; t,_=args_eval[2]
            return f'kuda_swap({s},{f},{t})', 'str'
        if name == 'caps':  s,_=args_eval[0]; return f'kuda_caps({s})', 'str'
        if name == 'small': s,_=args_eval[0]; return f'kuda_small({s})', 'str'
        if name == 'trim':  s,_=args_eval[0]; return f'kuda_trim({s})', 'str'
        if name == 'merge' and len(args_eval)==2:
            sep,_=args_eval[0]; lst,_=args_eval[1]
            return f'kuda_merge({sep}, {lst})', 'str'
        
        # List functions - standalone
        if name == 'add' and len(args_eval)==2:
            l,_=args_eval[0]; v,_=args_eval[1]
            self.emit(f'kuda_list_add({l}, {v});')
            return '0', 'double'
        if name == 'del' and len(args_eval)==2:
            l,_=args_eval[0]; v,_=args_eval[1]
            self.emit(f'kuda_list_del({l}, {v});')
            return '0', 'double'
        if name == 'sort':
            l,_=args_eval[0]
            self.emit(f'kuda_list_sort({l});')
            return '0', 'double'
        if name == 'rev':
            l,_=args_eval[0]
            self.emit(f'kuda_list_rev({l});')
            return '0', 'double'
        if name == 'grab':
            if len(args_eval) == 1:  # grab from list (pop)
                l,_=args_eval[0]; return f'kuda_list_pop({l})', 'double'
            elif len(args_eval) == 2:  # grab element at index
                l,_=args_eval[0]; idx,_=args_eval[1]; return f'kuda_list_grab({l}, (int)({idx}))', 'double'
        if name == 'fd' and len(args_eval)==2:
            l,_=args_eval[0]; v,_=args_eval[1]
            return f'((double)kuda_list_fd({l}, {v}))', 'double'
        if name == 'cnt' and len(args_eval)==2:
            l,_=args_eval[0]; v,_=args_eval[1]
            return f'((double)kuda_list_cnt({l}, {v}))', 'double'

        if name == 'write':
            f,_=args_eval[0]; c,_=args_eval[1]; tmp=self.fresh_tmp()
            self.emit(f'FILE* {tmp}=fopen({f},"w"); if({tmp}){{fprintf({tmp},"%s",{c});fclose({tmp});}}')
            return '0', 'double'
        if name == 'read':
            f,_=args_eval[0]; tmp=self.fresh_tmp(); buf=self.fresh_tmp()
            self.emit(f'char* {buf}=malloc(MAX_STR*16); {buf}[0]=0;')
            self.emit(f'FILE* {tmp}=fopen({f},"r"); if({tmp}){{fread({buf},1,MAX_STR*16-1,{tmp});fclose({tmp});}}')
            return buf, 'str'
        if name == 'append':
            f,_=args_eval[0]; c,_=args_eval[1]; tmp=self.fresh_tmp()
            self.emit(f'FILE* {tmp}=fopen({f},"a"); if({tmp}){{fprintf({tmp},"%s",{c});fclose({tmp});}}')
            return '0', 'double'
        if name == 'readlines':
            f,_=args_eval[0]; tmp=self.fresh_tmp(); buf=self.fresh_tmp(); lst=self.fresh_tmp()
            self.emit(f'KList* {lst}=kuda_list_new();')
            self.emit(f'FILE* {tmp}=fopen({f},"r");')
            self.emit(f'if({tmp}){{')
            self.emit(f'    char {buf}[MAX_STR];')
            self.emit(f'    while(fgets({buf},MAX_STR,{tmp})){{')
            self.emit('        int _l=strlen(' + buf + '); if(_l>0&&' + buf + '[_l-1]==\'\\n\'){' + buf + '[_l-1]=0;}'  )
            self.emit(f'        char* _s=malloc(strlen({buf})+1); strcpy(_s,{buf});')
            self.emit(f'        kuda_list_add_ptr({lst},(void*)_s);')
            self.emit(f'    }}')
            self.emit(f'    fclose({tmp});')
            self.emit(f'}}')
            return lst, 'strlist'
        # Macierze
        if name == 'Matrix':     r,_=args_eval[0];c,_=args_eval[1]; return f'kuda_mat_new((int)({r}),(int)({c}))', 'matrix'
        if name == 'mat_rand':   r,_=args_eval[0];c,_=args_eval[1]; return f'kuda_mat_rand((int)({r}),(int)({c}))', 'matrix'
        if name == 'mat_zeros':  r,_=args_eval[0];c,_=args_eval[1]; return f'kuda_mat_new((int)({r}),(int)({c}))', 'matrix'
        if name == 'MatrixRand': r,_=args_eval[0];c,_=args_eval[1]; return f'kuda_mat_rand((int)({r}),(int)({c}))', 'matrix'
        if name == 'mat_get':    m,_=args_eval[0];r,_=args_eval[1];c,_=args_eval[2]; return f'kuda_mat_get({m},(int)({r}),(int)({c}))', 'double'
        if name == 'mat_set':
            m,_=args_eval[0];r,_=args_eval[1];c,_=args_eval[2];v,_=args_eval[3]
            self.emit(f'kuda_mat_set({m},(int)({r}),(int)({c}),{v});'); return '0', 'double'
        if name == 'mat_mul':     a,_=args_eval[0];b,_=args_eval[1]; return f'kuda_mat_mul({a},{b})', 'matrix'
        if name == 'mat_add':     a,_=args_eval[0];b,_=args_eval[1]; return f'kuda_mat_add({a},{b})', 'matrix'
        if name == 'mat_sub':     a,_=args_eval[0];b,_=args_eval[1]; return f'kuda_mat_sub({a},{b})', 'matrix'
        if name == 'mat_scale':   m,_=args_eval[0];s,_=args_eval[1]; return f'kuda_mat_scale({m},{s})', 'matrix'
        if name == 'mat_T':       m,_=args_eval[0]; return f'kuda_mat_T({m})', 'matrix'
        if name == 'mat_hadamard':a,_=args_eval[0];b,_=args_eval[1]; return f'kuda_mat_hadamard({a},{b})', 'matrix'
        if name == 'mat_copy':    m,_=args_eval[0]; return f'kuda_mat_copy({m})', 'matrix'
        if name == 'mat_print':   m,_=args_eval[0]; self.emit(f'kuda_mat_print({m});'); return '0', 'double'
        if name == 'mat_sum':     m,_=args_eval[0]; return f'kuda_mat_sum({m})', 'double'
        if name == 'mat_mean':    m,_=args_eval[0]; return f'kuda_mat_mean({m})', 'double'
        if name == 'dot':         a,_=args_eval[0];b,_=args_eval[1]; return f'kuda_dot({a},{b})', 'double'

        # ML
        if name == 'sigmoid':          val,_=args_eval[0]; return f'kuda_sigmoid({val})', 'double'
        if name == 'relu':             val,_=args_eval[0]; return f'kuda_relu({val})', 'double'
        if name == 'mat_sigmoid':      m,_=args_eval[0]; return f'kuda_mat_sigmoid({m})', 'matrix'
        if name == 'mat_sigmoid_deriv':m,_=args_eval[0]; return f'kuda_mat_sigmoid_deriv({m})', 'matrix'
        if name == 'mat_relu':         m,_=args_eval[0]; return f'kuda_mat_relu({m})', 'matrix'
        if name == 'mat_relu_deriv':   m,_=args_eval[0]; return f'kuda_mat_relu_deriv({m})', 'matrix'
        if name == 'mat_tanh':         m,_=args_eval[0]; return f'kuda_mat_tanh({m})', 'matrix'
        if name == 'mse':
            p,ptyp=args_eval[0]; t,ttyp=args_eval[1]
            if ptyp == 'matrix': return f'kuda_mse({p},{t})', 'double'
            return f'kuda_mse_scalar({p},{t})', 'double'
        if name == 'mse_grad':         p,_=args_eval[0];t,_=args_eval[1]; return f'kuda_mse_grad({p},{t})', 'matrix'

        # Model constructor: Hero("adam") -> Hero_new("adam")
        if name in self.models:
            args_str = ', '.join(v for v, t in args_eval)
            return f'{name}_new({args_str})', name

        # Rename user-defined 'main' to avoid conflict with C main
        c_name = 'kuda_main' if name == 'main' else name

        # User function call - pass model pointers and strings as-is, cast others to double
        arg_parts = []
        for v, t in args_eval:
            if t in self.models or t == 'str':
                arg_parts.append(v)
            else:
                arg_parts.append(f'(double)({v})')
        args_str = ', '.join(arg_parts)
        # Sprawdz czy to extern funkcja
        if name in self.extern_funcs:
            ext_ret = self.extern_funcs[name]
            c_ret = {'double': 'double', 'str': 'str', 'void': 'double', 'int': 'double'}.get(ext_ret, 'double')
            # dla extern przekazujemy argumenty bez castowania
            ext_args = ', '.join(v for v, t in args_eval)
            return f'{name}({ext_args})', c_ret
        # Return the function's known return type
        ret_type = self.func_return_types.get(name, 'double')
        return f'{c_name}({args_str})', ret_type

    def _gen_method_call(self, attr_node, arg_nodes):
        obj_val, obj_typ = self._gen_expr(attr_node.obj)
        method = attr_node.attr
        args_eval = [self._gen_expr(a) for a in arg_nodes]

        # Net predict call: xor.predict([1.0, 0.0]) -> xor_predict(tmp_arr)
        if obj_typ == 'net' and method == 'predict':
            arg_val, _ = args_eval[0] if args_eval else ('NULL', 'list')
            tmp = self._tmp_var()
            info = self._net_info.get(obj_val, {})
            n_in   = info.get('n_inputs',  2)
            n_out  = info.get('n_outputs', 1)
            layers = info.get('layers', [])
            self.emit(f'double {tmp}_arr[{n_in}];')
            self.emit(f'for(int _i=0;_i<{n_in};_i++) {tmp}_arr[_i]=kuda_list_grab({arg_val},_i);')
            if n_out == 1:
                # single output — return double (backward compat)
                return f'{obj_val}_predict({tmp}_arr)', 'double'
            else:
                # multi-output — return KList
                self.emit(f'double {tmp}_out[{n_out}];')
                self.emit(f'{obj_val}_predict_all({tmp}_arr, {tmp}_out);')
                self.emit(f'KList* {tmp}_lst = kuda_list_new();')
                self.emit(f'for(int _j=0;_j<{n_out};_j++) kuda_list_add({tmp}_lst, {tmp}_out[_j]);')
                return f'{tmp}_lst', 'list'

        # Net write call: mynet.write("file.json") -> save weights to JSON
        if obj_typ == 'net' and method == 'write':
            filename_val, _ = args_eval[0] if args_eval else ('"weights.json"', 'str')
            info = self._net_info.get(obj_val, {})
            layers = info.get('layers', [])
            n_layers = len(layers)
            n_weights = sum(layers[i]*layers[i+1] for i in range(n_layers-1))
            n_biases  = sum(layers[i+1] for i in range(n_layers-1))
            tmp = self._tmp_var()
            self.emit(f'{{ FILE* {tmp}_f = fopen({filename_val}, "w");')
            self.emit(f'  if({tmp}_f) {{')
            self.emit(f'    fprintf({tmp}_f, "{{\\n");')
            self.emit(f'    fprintf({tmp}_f, "  \\"net\\": \\"{obj_val}\\",\\n");')
            self.emit(f'    fprintf({tmp}_f, "  \\"layers\\": [");')
            for i, l in enumerate(layers):
                comma = ',' if i < n_layers - 1 else ''
                self.emit(f'    fprintf({tmp}_f, "{l}{comma}");')
            self.emit(f'    fprintf({tmp}_f, "],\\n");')
            self.emit(f'    fprintf({tmp}_f, "  \\"W\\": [");')
            self.emit(f'    for(int _wi=0; _wi<{n_weights}; _wi++) {{')
            self.emit(f'      if(_wi < {n_weights}-1) fprintf({tmp}_f, "%.10f,", {obj_val}_W[_wi]);')
            self.emit(f'      else fprintf({tmp}_f, "%.10f", {obj_val}_W[_wi]);')
            self.emit(f'    }}')
            self.emit(f'    fprintf({tmp}_f, "],\\n");')
            self.emit(f'    fprintf({tmp}_f, "  \\"B\\": [");')
            self.emit(f'    for(int _bi=0; _bi<{n_biases}; _bi++) {{')
            self.emit(f'      if(_bi < {n_biases}-1) fprintf({tmp}_f, "%.10f,", {obj_val}_B[_bi]);')
            self.emit(f'      else fprintf({tmp}_f, "%.10f", {obj_val}_B[_bi]);')
            self.emit(f'    }}')
            self.emit(f'    fprintf({tmp}_f, "]\\n");')
            self.emit(f'    fprintf({tmp}_f, "}}\\n");')
            self.emit(f'    fclose({tmp}_f);')
            self.emit(f'    printf("Wagi zapisane do %s\\n", {filename_val});')
            self.emit(f'  }}')
            self.emit(f'}}')
            return 'NULL', 'str'

        # Net load call: mynet.load("file.json") -> load weights from JSON
        if obj_typ == 'net' and method == 'load':
            filename_val, _ = args_eval[0] if args_eval else ('"weights.json"', 'str')
            info = self._net_info.get(obj_val, {})
            layers = info.get('layers', [])
            n_layers = len(layers)
            n_weights = sum(layers[i]*layers[i+1] for i in range(n_layers-1))
            n_biases  = sum(layers[i+1] for i in range(n_layers-1))
            tmp = self._tmp_var()
            self.emit(f'{{ FILE* {tmp}_f = fopen({filename_val}, "r");')
            self.emit(f'  if({tmp}_f) {{')
            self.emit(f'    char {tmp}_buf[32];')
            self.emit(f'    int {tmp}_wi = 0, {tmp}_bi = 0;')
            self.emit(f'    int {tmp}_in_w = 0, {tmp}_in_b = 0;')
            self.emit(f'    int {tmp}_c;')
            # simple char-by-char parser: find "W": [ then read doubles, then "B": [
            self.emit(f'    // skip to "W":[')
            self.emit(f'    while(({tmp}_c = fgetc({tmp}_f)) != EOF) {{')
            self.emit(f'      if({tmp}_c == \'W\' && !{tmp}_in_w && !{tmp}_in_b) {{')
            self.emit(f'        fgetc({tmp}_f); fgetc({tmp}_f); fgetc({tmp}_f); // skip ":[')
            self.emit(f'        {tmp}_in_w = 1;')
            self.emit(f'      }} else if({tmp}_c == \'B\' && {tmp}_wi >= {n_weights} && !{tmp}_in_b) {{')
            self.emit(f'        fgetc({tmp}_f); fgetc({tmp}_f); fgetc({tmp}_f); // skip ":[')
            self.emit(f'        {tmp}_in_b = 1; {tmp}_in_w = 0;')
            self.emit(f'      }} else if({tmp}_in_w && ({tmp}_c == \'-\' || ({tmp}_c >= \'0\' && {tmp}_c <= \'9\'))) {{')
            self.emit(f'        ungetc({tmp}_c, {tmp}_f);')
            self.emit(f'        double {tmp}_v; fscanf({tmp}_f, "%lf", &{tmp}_v);')
            self.emit(f'        if({tmp}_wi < {n_weights}) {obj_val}_W[{tmp}_wi++] = {tmp}_v;')
            self.emit(f'      }} else if({tmp}_in_b && ({tmp}_c == \'-\' || ({tmp}_c >= \'0\' && {tmp}_c <= \'9\'))) {{')
            self.emit(f'        ungetc({tmp}_c, {tmp}_f);')
            self.emit(f'        double {tmp}_v2; fscanf({tmp}_f, "%lf", &{tmp}_v2);')
            self.emit(f'        if({tmp}_bi < {n_biases}) {obj_val}_B[{tmp}_bi++] = {tmp}_v2;')
            self.emit(f'      }}')
            self.emit(f'    }}')
            self.emit(f'    fclose({tmp}_f);')
            self.emit(f'    printf("Wagi wczytane z %s\\n", {filename_val});')
            self.emit(f'  }} else {{ printf("Blad: nie mozna otworzyc %s\\n", {filename_val}); }}')
            self.emit(f'}}')
            return 'NULL', 'str'

        # Model instance method call: hero.bark() -> Hero_bark(hero)
        if obj_typ in self.models:
            args_str = ', '.join(v for v, t in args_eval)
            full_args = obj_val + (f', {args_str}' if args_str else '')
            return f'{obj_typ}_{method}({full_args})', 'double'

        # self.method() inside a model method
        if obj_val == 'self' and '_self_model' in self.vars:
            model_name = self.vars['_self_model']
            args_str = ', '.join(v for v, t in args_eval)
            full_args = 'self' + (f', {args_str}' if args_str else '')
            return f'{model_name}_{method}({full_args})', 'double'

        if obj_typ == 'matrix':
            if method == 'T':             return f'kuda_mat_T({obj_val})', 'matrix'
            if method == 'sigmoid':       return f'kuda_mat_sigmoid({obj_val})', 'matrix'
            if method == 'relu':          return f'kuda_mat_relu({obj_val})', 'matrix'
            if method == 'tanh':          return f'kuda_mat_tanh({obj_val})', 'matrix'
            if method == 'sigmoid_deriv': return f'kuda_mat_sigmoid_deriv({obj_val})', 'matrix'
            if method == 'relu_deriv':    return f'kuda_mat_relu_deriv({obj_val})', 'matrix'
            if method == 'copy':          return f'kuda_mat_copy({obj_val})', 'matrix'
            if method == 'sum':           return f'kuda_mat_sum({obj_val})', 'double'
            if method == 'mean':          return f'kuda_mat_mean({obj_val})', 'double'
            if method == 'print':         self.emit(f'kuda_mat_print({obj_val});'); return '0', 'double'
            if method == 'scale' and args_eval:
                s,_=args_eval[0]; return f'kuda_mat_scale({obj_val},{s})', 'matrix'
            if method == 'get' and len(args_eval)==2:
                r,_=args_eval[0];c,_=args_eval[1]; return f'kuda_mat_get({obj_val},(int)({r}),(int)({c}))', 'double'
            if method == 'set' and len(args_eval)==3:
                r,_=args_eval[0];c,_=args_eval[1];v,_=args_eval[2]
                self.emit(f'kuda_mat_set({obj_val},(int)({r}),(int)({c}),{v});'); return '0', 'double'

        if obj_typ == 'str':
            if method == 'caps':  return f'kuda_caps({obj_val})', 'str'
            if method == 'small': return f'kuda_small({obj_val})', 'str'
            if method == 'trim':  return f'kuda_trim({obj_val})', 'str'
            if method == 'len':   return f'((double)strlen({obj_val}))', 'double'
            if method == 'swap' and len(args_eval)==2:
                a,_=args_eval[0];b,_=args_eval[1]; return f'kuda_swap({obj_val},{a},{b})', 'str'
            if method == 'cut':
                delim = args_eval[0][0] if args_eval else '" "'
                return f'kuda_cut({obj_val}, {delim})', 'strlist'

        if obj_typ == 'list':
            if method == 'add' and args_eval:
                v, vtyp = args_eval[0]
                if vtyp in ('list', 'strlist'):
                    self.emit(f'kuda_list_add_ptr({obj_val}, {v});')
                else:
                    self.emit(f'kuda_list_add({obj_val}, {v});')
                return '0', 'double'
            if method == 'del' and args_eval:
                v,_=args_eval[0]; self.emit(f'kuda_list_del({obj_val}, {v});'); return '0', 'double'
            if method == 'sort':
                self.emit(f'kuda_list_sort({obj_val});'); return '0', 'double'
            if method == 'rev':
                self.emit(f'kuda_list_rev({obj_val});'); return '0', 'double'
            if method == 'grab':
                if not args_eval:  # pop
                    return f'kuda_list_pop({obj_val})', 'double'
                else:  # get at index
                    idx,_=args_eval[0]; return f'kuda_list_grab({obj_val}, (int)({idx}))', 'double'
            if method == 'fd' and args_eval:
                v,_=args_eval[0]; return f'((double)kuda_list_fd({obj_val}, {v}))', 'double'
            if method == 'cnt' and args_eval:
                v,_=args_eval[0]; return f'((double)kuda_list_cnt({obj_val}, {v}))', 'double'
            if method == 'len':
                return f'((double){obj_val}->len)', 'double'

        return '0', 'double'