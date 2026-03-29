"""
net.py — Kuda neural network C code generator.
Handles NetNode -> C code generation, separated from main codegen.
"""

import math
import random as _random


def gen_net_c(node, interp_eval_fn):
    """
    Generate C code for a net block.

    Args:
        node: NetNode from parser
        interp_eval_fn: function(val_node) -> Python value, from interpreter

    Returns:
        (lines: list[str], info: dict)
    """

    # Step 1: evaluate params
    params = {}
    for key, val_node in node.params.items():
        try:
            params[key] = interp_eval_fn(val_node)
        except Exception:
            params[key] = None

    # Step 2: get dataset
    raw_data = params.get('data') or []
    if not raw_data and 'inputs' in params and 'targets' in params:
        raw_data = list(zip(params['inputs'], params['targets']))

    dataset = []
    for item in raw_data:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            inp, tgt = item
            if not isinstance(inp, list): inp = [inp]
            if not isinstance(tgt, list): tgt = [tgt]
            dataset.append((inp, tgt))

    n_inputs  = len(dataset[0][0]) if dataset else 1
    n_outputs = len(dataset[0][1]) if dataset else 1

    # Step 3: resolve layers
    layers_raw = params.get('layers', [n_inputs, 8, n_outputs])
    layers = []
    for l in layers_raw:
        if l is None or (isinstance(l, str) and l == 'auto'):
            layers.append(n_inputs)
        else:
            layers.append(int(l))
    # Only auto-fix layer[0] if we actually have dataset info
    # If dataset is empty (runtime inputs), trust the explicit layers value
    if dataset and layers[0] != n_inputs:
        layers[0] = n_inputs
    # Update n_inputs/n_outputs from layers when dataset unavailable
    if not dataset:
        n_inputs  = layers[0]
        n_outputs = layers[-1]

    # Step 4: hyperparams
    lr        = float(params.get('lr', 0.01))
    epochs    = int(params.get('epochs', 1000))
    act_name  = params.get('act', 'tanh')
    out_name  = params.get('act_out', act_name)
    init_name = params.get('init', 'xav')
    log_every = int(params.get('log', 100))
    # ~verbose = False silences training output (overrides ~log)
    verbose = params.get('verbose', True)
    if verbose is False or verbose == 0:
        log_every = 0
    stop_loss = float(params.get('stop', -1.0))

    name     = node.name
    n_layers = len(layers)

    # Step 5: initialize weights
    def init_w(n_in, n_out, method):
        std = math.sqrt(2.0 / n_in) if method == 'he' else math.sqrt(2.0 / (n_in + n_out))
        return [_random.gauss(0, std) for _ in range(n_in * n_out)]

    all_weights, all_biases = [], []
    for i in range(n_layers - 1):
        all_weights.append(init_w(layers[i], layers[i+1], init_name))
        all_biases.append([0.0] * layers[i+1])

    flat_w = [w for layer in all_weights for w in layer]
    flat_b = [b for layer in all_biases  for b in layer]

    # Step 6: flatten dataset
    n_samples = len(dataset)
    inp_flat  = [x for inp, _ in dataset for x in inp]
    tgt_flat  = [x for _, tgt in dataset for x in tgt]

    # Activation function C names
    act_c = {
        'tanh':    'kuda_tanh_act',
        'sigmoid': 'kuda_sigmoid',
        'relu':    'kuda_relu',
        'leaky':   'kuda_leaky',
        'linear':  'kuda_linear_act',
    }
    act_d_c = {
        'tanh':    'kuda_tanh_d',
        'sigmoid': 'kuda_sigmoid_d',
        'relu':    'kuda_relu_d',
        'leaky':   'kuda_leaky_d',
        'linear':  'kuda_linear_d',
    }

    af   = act_c.get(act_name,  'kuda_tanh_act')
    af_d = act_d_c.get(act_name, 'kuda_tanh_d')
    of   = act_c.get(out_name,  af)
    of_d = act_d_c.get(out_name, af_d)

    NAME = name.upper()
    max_layer = max(layers)

    layer_str = ', '.join(str(l) for l in layers)
    w_str   = ', '.join(f'{w:.10f}' for w in flat_w)
    b_str   = ', '.join(f'{b:.10f}' for b in flat_b)
    inp_str = ', '.join(f'{x:.6f}'  for x in inp_flat)
    tgt_str = ', '.join(f'{x:.6f}'  for x in tgt_flat)

    L = []  # output lines

    L.append(f'/* === Net: {name} === */')
    L.append(f'static int    {name}_layers[]   = {{{layer_str}}};')
    L.append(f'static int    {name}_n_layers   = {n_layers};')
    L.append(f'static double {name}_W[]        = {{{w_str}}};')
    L.append(f'static double {name}_B[]        = {{{b_str}}};')
    L.append(f'static double {name}_data_in[]  = {{{inp_str}}};')
    L.append(f'static double {name}_data_tgt[] = {{{tgt_str}}};')
    L.append(f'static int    {name}_n_samples  = {n_samples};')
    L.append(f'static int    {name}_n_inputs   = {n_inputs};')
    L.append(f'static int    {name}_n_outputs  = {n_outputs};')
    L.append('')

    # per-net activation wrappers
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

    # forward pass
    L.append(f'static void {name}_forward(double* input, double acts[][{NAME}_MAX_LAYER]) {{')
    L.append(f'    for(int j=0; j<{name}_layers[0]; j++) acts[0][j] = input[j];')
    L.append(f'    int w_off=0, b_off=0;')
    L.append(f'    for(int li=0; li<{name}_n_layers-1; li++) {{')
    L.append(f'        int ni={name}_layers[li], no={name}_layers[li+1];')
    L.append(f'        int is_last = (li == {name}_n_layers-2);')
    L.append(f'        for(int j=0; j<no; j++) {{')
    L.append(f'            double z = {name}_B[b_off+j];')
    L.append(f'            for(int k=0; k<ni; k++) z += acts[li][k] * {name}_W[w_off + j*ni + k];')
    L.append(f'            acts[li+1][j] = {name}_act_fn(z, is_last);')
    L.append(f'        }}')
    L.append(f'        w_off += ni*no; b_off += no;')
    L.append(f'    }}')
    L.append(f'}}')
    L.append('')

    # predict — fills output array, returns first value for single-output compat
    L.append(f'static void {name}_predict_all(double* input, double* out_arr) {{')
    L.append(f'    double acts[{NAME}_N_LAYERS][{NAME}_MAX_LAYER];')
    L.append(f'    {name}_forward(input, acts);')
    L.append(f'    int last = {name}_n_layers-1;')
    L.append(f'    for(int j=0; j<{name}_layers[last]; j++) out_arr[j] = acts[last][j];')
    L.append(f'}}')
    L.append(f'static double {name}_predict(double* input) {{')
    L.append(f'    double _out[{NAME}_MAX_LAYER];')
    L.append(f'    {name}_predict_all(input, _out);')
    L.append(f'    return _out[0];')
    L.append(f'}}')
    L.append('')

    # train
    L.append(f'static void {name}_train() {{')
    L.append(f'    const int epochs    = {epochs};')
    L.append(f'    const double lr     = {lr};')
    L.append(f'    const double stop   = {stop_loss};')
    L.append(f'    const int log_every = {log_every};')
    L.append(f'    const int n  = {name}_n_samples;')
    L.append(f'    const int ni = {name}_n_inputs;')
    L.append(f'    const int no = {name}_n_outputs;')
    L.append(f'    double acts  [{NAME}_N_LAYERS][{NAME}_MAX_LAYER];')
    L.append(f'    double deltas[{NAME}_N_LAYERS][{NAME}_MAX_LAYER];')
    L.append(f'    for(int ep=0; ep<epochs; ep++) {{')
    L.append(f'        double total_loss = 0.0;')
    L.append(f'        for(int s=0; s<n; s++) {{')
    L.append(f'            double* inp = {name}_data_in  + s*ni;')
    L.append(f'            double* tgt = {name}_data_tgt + s*no;')
    L.append(f'            {name}_forward(inp, acts);')
    L.append(f'            int last = {name}_n_layers-1;')
    L.append(f'            for(int j=0; j<{name}_layers[last]; j++)')
    L.append(f'                deltas[last][j] = (acts[last][j]-tgt[j]) * {name}_act_d_fn(acts[last][j],1);')
    L.append(f'            for(int j=0; j<no; j++)')
    L.append(f'                total_loss += (acts[last][j]-tgt[j])*(acts[last][j]-tgt[j]);')
    L.append(f'            /* hidden deltas — compute weight offset for layer li->li+1 on the fly */')
    L.append(f'            for(int li={name}_n_layers-2; li>0; li--) {{')
    L.append(f'                int cur={name}_layers[li], nxt={name}_layers[li+1];')
    L.append(f'                int wo=0;')
    L.append(f'                for(int _l=0; _l<li; _l++) wo += {name}_layers[_l]*{name}_layers[_l+1];')
    L.append(f'                for(int j=0; j<cur; j++) {{')
    L.append(f'                    double err=0;')
    L.append(f'                    for(int k=0; k<nxt; k++) err += deltas[li+1][k] * {name}_W[wo + k*cur + j];')
    L.append(f'                    deltas[li][j] = err * {name}_act_d_fn(acts[li][j], 0);')
    L.append(f'                }}')
    L.append(f'            }}')
    L.append(f'            /* weight update */')
    L.append(f'            int w_off=0, b_off=0;')
    L.append(f'            for(int li=0; li<{name}_n_layers-1; li++) {{')
    L.append(f'                int cur={name}_layers[li], nxt={name}_layers[li+1];')
    L.append(f'                for(int j=0; j<nxt; j++) {{')
    L.append(f'                    {name}_B[b_off+j] -= lr * deltas[li+1][j];')
    L.append(f'                    for(int k=0; k<cur; k++)')
    L.append(f'                        {name}_W[w_off + j*cur + k] -= lr * deltas[li+1][j] * acts[li][k];')
    L.append(f'                }}')
    L.append(f'                w_off += cur*nxt; b_off += nxt;')
    L.append(f'            }}')
    L.append(f'        }}')
    L.append(f'        double avg_loss = total_loss / n;')
    if log_every > 0:
        L.append(f'        if(ep % {log_every} == 0)')
        L.append(f'            printf("Epoch %d | Loss: %.6f\\n", ep, avg_loss);')
    L.append(f'        if(stop > 0 && avg_loss < stop) {{')
    if log_every > 0:
        L.append(f'            printf("Early stop epoch %d | Loss: %.6f\\n", ep, avg_loss);')
    L.append(f'            break;')
    L.append(f'        }}')
    L.append(f'    }}')
    L.append(f'}}')
    L.append('')

    info = {
        'layers':   layers,
        'n_inputs': n_inputs,
        'n_outputs': n_outputs,
    }
    return L, info