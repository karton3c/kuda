# Kuda v0.2.1 - C Code Generator with Full Builtins Support
from parser import *
import math

class CompileError(Exception):
    def __init__(self, msg):
        super().__init__(f'[Kuda CompileError] {msg}')


class CGenerator:
    def __init__(self):
        self.lines = []
        self.indent = 0
        self.tmp_count = 0
        self.vars = {}
        self.functions = {}
        self.includes = set()

    def fresh_tmp(self):
        self.tmp_count += 1
        return f'_t{self.tmp_count}'

    def emit(self, line=''):
        self.lines.append('    ' * self.indent + line)

    def generate(self, ast):
        self.includes.add('#include <stdio.h>')
        self.includes.add('#include <stdlib.h>')
        self.includes.add('#include <string.h>')
        self.includes.add('#include <math.h>')
        self.includes.add('#include <time.h>')
        self.includes.add('#include <unistd.h>')
        self.includes.add('#include <ctype.h>')
        self.includes.add('#include <stdint.h>')

        func_decls = []
        main_stmts = []
        for stmt in ast.statements:
            if isinstance(stmt, FunNode):
                func_decls.append(stmt)
            else:
                main_stmts.append(stmt)

        runtime = self._runtime()

        func_code = []
        for f in func_decls:
            func_code.extend(self._gen_function(f))

        self.emit('int main(int argc, char *argv[]) {')
        self.indent += 1
        self.emit('srand(time(NULL));')
        for stmt in main_stmts:
            self._gen_stmt(stmt)
        self.emit('return 0;')
        self.indent -= 1
        self.emit('}')

        main_code = self.lines
        final = []
        final.extend(sorted(self.includes))
        final.append('')
        final.extend(runtime)
        final.append('')
        final.extend(func_code)
        final.append('')
        final.extend(main_code)
        return '\n'.join(final)

    def _runtime(self):
        return [
            '/* Kuda v0.2.1 Runtime - Full Featured */',
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
            'double kuda_dot(KMatrix* A,KMatrix* B){double s=0;for(int i=0;i<A->rows;i++) for(int j=0;j<A->cols;j++) s+=A->data[i][j]*B->data[i][j];return s;}',
            '',
            '/* Activation functions */',
            'double kuda_sigmoid(double x){return 1.0/(1.0+exp(-x));}',
            'double kuda_relu(double x){return x>0?x:0;}',
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

    def _gen_function(self, node):
        old_lines, old_indent, old_vars = self.lines, self.indent, dict(self.vars)
        self.lines = []; self.indent = 0
        if isinstance(node, FunNode):
            params = ', '.join(f'double {p}' for p in node.params)
            self.emit(f'double {node.name}({params}) {{')
            self.indent += 1
            for p in node.params:
                self.vars[p] = 'double'
            for stmt in node.body:
                self._gen_stmt(stmt)
            self.emit('return 0;')
            self.indent -= 1
            self.emit('}')
        result = self.lines
        self.lines, self.indent, self.vars = old_lines, old_indent, old_vars
        return result

    def _gen_stmt(self, node):
        if node is None: return
        if isinstance(node, AssignNode): self._gen_assign(node)
        elif isinstance(node, OutNode): self._gen_out(node)
        elif isinstance(node, IfNode): self._gen_if(node)
        elif isinstance(node, RepeatNode): self._gen_repeat(node)
        elif isinstance(node, EachNode): self._gen_each(node)
        elif isinstance(node, TilNode): self._gen_til(node)
        elif isinstance(node, FunNode): pass
        elif isinstance(node, GiveNode):
            val, _ = self._gen_expr(node.value)
            self.emit(f'return (double)({val});')
        elif isinstance(node, TryNode):
            for s in node.try_body: self._gen_stmt(s)
        elif isinstance(node, BreakNode): self.emit('break;')
        elif isinstance(node, ContinueNode): self.emit('continue;')
        elif isinstance(node, UseNode): pass
        else:
            try:
                val, _ = self._gen_expr(node)
                self.emit(f'{val};')
            except: pass

    def _gen_assign(self, node):
        if isinstance(node.name, str):
            val, typ = self._gen_expr(node.value)
            if node.name not in self.vars:
                self.vars[node.name] = typ
                if typ == 'str':     self.emit(f'char* {node.name} = {val};')
                elif typ == 'bool':  self.emit(f'int {node.name} = {val};')
                elif typ == 'matrix':self.emit(f'KMatrix* {node.name} = {val};')
                elif typ == 'list':  self.emit(f'KList* {node.name} = {val};')
                else:                self.emit(f'double {node.name} = {val};')
            else:
                self.emit(f'{node.name} = {val};')
        elif isinstance(node.name, AttrNode):
            obj_val, _ = self._gen_expr(node.name.obj)
            val, _ = self._gen_expr(node.value)
            attr = node.name.attr
            obj_typ = self.vars.get(node.name.obj.name if isinstance(node.name.obj, IdentNode) else '', '')
            if obj_typ == 'matrix':
                # mat_set przez set(row, col, val) - obsluzone przez metodę
                pass
            else:
                self.emit(f'{obj_val}.{attr} = {val};')

    def _gen_out(self, node):
        val, typ = self._gen_expr(node.value)
        if typ == 'str':    self.emit(f'kuda_print_str({val});')
        elif typ == 'list':   self.emit(f'kuda_print_list({val});')
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
                if len(args) == 1:
                    end, _ = self._gen_expr(args[0])
                    self.vars[node.var] = 'double'
                    self.emit(f'for (double {node.var} = 0; {node.var} < {end}; {node.var}++) {{')
                elif len(args) == 2:
                    start, _ = self._gen_expr(args[0]); end, _ = self._gen_expr(args[1])
                    self.vars[node.var] = 'double'
                    self.emit(f'for (double {node.var} = {start}; {node.var} < {end}; {node.var}++) {{')
                self.indent += 1
                for s in node.body: self._gen_stmt(s)
                self.indent -= 1
                self.emit('}')
                return
        self.emit('/* each - wymaga interpretera */')

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
        if isinstance(node, ListNode):
            # Create a new list and add all elements
            tmp = self.fresh_tmp()
            self.emit(f'KList* {tmp} = kuda_list_new();')
            for elem in node.elements:
                val, _ = self._gen_expr(elem)
                self.emit(f'kuda_list_add({tmp}, {val});')
            return tmp, 'list'
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
            if otyp == 'list':
                return f'kuda_list_grab({obj}, (int)({idx}))', 'double'
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
        if ltyp == 'matrix' or rtyp == 'matrix':
            if op == '+': return f'kuda_mat_add({lval}, {rval})', 'matrix'
            if op == '-': return f'kuda_mat_sub({lval}, {rval})', 'matrix'
            if op == '*':
                if ltyp == 'matrix' and rtyp == 'matrix': return f'kuda_mat_mul({lval}, {rval})', 'matrix'
                if ltyp == 'matrix': return f'kuda_mat_scale({lval}, {rval})', 'matrix'
                return f'kuda_mat_scale({rval}, {lval})', 'matrix'
        if op == '%': return f'((double)fmod((double)({lval}),(double)({rval})))', 'double'
        typ = 'bool' if op in ('==','!=','<','>','<=','>=') else 'double'
        return f'({lval} {op} {rval})', typ

    def _gen_attr_access(self, node):
        obj_val, obj_typ = self._gen_expr(node.obj)
        if obj_typ == 'matrix':
            if node.attr == 'rows': return f'((double){obj_val}->rows)', 'double'
            if node.attr == 'cols': return f'((double){obj_val}->cols)', 'double'
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
            return (val, 'str') if typ == 'str' else (f'kuda_double_to_str({val})', 'str')
        if name == 'int':   val, _ = args_eval[0]; return f'((double)(long long)({val}))', 'double'
        if name == 'float': val, _ = args_eval[0]; return f'((double)({val}))', 'double'
        if name == 'abs':   val, _ = args_eval[0]; return f'fabs({val})', 'double'
        if name == 'round': val, _ = args_eval[0]; return f'round({val})', 'double'
        if name == 'exp':   val, _ = args_eval[0]; return f'exp({val})', 'double'
        if name == 'log':   val, _ = args_eval[0]; return f'log({val})', 'double'
        if name == 'prw':   val, _ = args_eval[0]; return f'sqrt({val})', 'double'
        if name == 'dwn':   val, _ = args_eval[0]; return f'floor({val})', 'double'
        if name == 'up':    val, _ = args_eval[0]; return f'ceil({val})', 'double'
        if name == 'pot':   b,_ = args_eval[0]; e,_ = args_eval[1]; return f'pow({b},{e})', 'double'
        if name == 'max' and len(args_eval)==2: a,_=args_eval[0];b,_=args_eval[1]; return f'fmax({a},{b})', 'double'
        if name == 'min' and len(args_eval)==2: a,_=args_eval[0];b,_=args_eval[1]; return f'fmin({a},{b})', 'double'
        if name == 'rand':       lo,_=args_eval[0];hi,_=args_eval[1]; return f'((double)kuda_rand((int)({lo}),(int)({hi})))', 'double'
        if name == 'rand_float': return 'kuda_rand_float()', 'double'
        if name == 'wait':       val,_=args_eval[0]; return f'sleep((int)({val}))', 'double'
        if name == 'time':       return '((double)clock()/CLOCKS_PER_SEC)', 'double'
        if name == 'input':      p = args_eval[0][0] if args_eval else '""'; return f'kuda_input({p})', 'str'
        
        # String functions
        if name == 'len':
            val,typ=args_eval[0]
            if typ=='str': return f'((double)strlen({val}))', 'double'
            if typ=='list': return f'((double){val}->len)', 'double'
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
        if name == 'mse':              p,_=args_eval[0];t,_=args_eval[1]; return f'kuda_mse({p},{t})', 'double'
        if name == 'mse_grad':         p,_=args_eval[0];t,_=args_eval[1]; return f'kuda_mse_grad({p},{t})', 'matrix'

        # Funkcja użytkownika
        args_str = ', '.join(
            f'(double)(intptr_t)({v})' if t=='str' else f'(double)({v})'
            for v, t in args_eval
        )
        return f'{name}({args_str})', 'double'

    def _gen_method_call(self, attr_node, arg_nodes):
        obj_val, obj_typ = self._gen_expr(attr_node.obj)
        method = attr_node.attr
        args_eval = [self._gen_expr(a) for a in arg_nodes]

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
                return f'kuda_cut({obj_val}, {delim})', 'list'

        if obj_typ == 'list':
            if method == 'add' and args_eval:
                v,_=args_eval[0]; self.emit(f'kuda_list_add({obj_val}, {v});'); return '0', 'double'
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