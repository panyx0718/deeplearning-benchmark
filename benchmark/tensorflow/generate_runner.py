import sys, getopt, os

num_workers = None
script_to_run = None
gen_dir = None
gen_dir_rel = None
batch_size = None
gpu_per_host = None

def get_nodes(nodes_file):
    with open(nodes_file) as f:
        lines = f.read().splitlines()
        
    nodes = [s.split()[0] for s in lines if s]
    return nodes


def get_worker_list(nodes, gpu_per_node):
    lst = []
    for node in nodes:
      lst.append( node + ":2230")
    return ','.join(lst)

def get_ps_list(nodes):
    return ','.join( [n + ":2222" for n in nodes] )
    
def get_script(script_name, remote_dir, workers_list, ps_list, index, batch_size, gpu_per_node):

    sys.stderr.write('%s\n' % os.path.dirname(os.path.realpath(__file__)))
    script = ''

    script += 'rm -rf /tmp/imagenet_train/'
    script += '\n'    
    script += 'rm -f /tmp/worker*'
    script += '\n'
    script += "export PYTHONPATH='"+remote_dir+"/inception'"
    script += '\n'

    script += '\n\n'
    
    script += "CUDA_VISIBLE_DEVICES='' python /tmp/tf_cnn_benchmarks.py " \
                + "--model=inception3 " \
                + "--batch_size=" + str(batch_size) + " " \
                + "--ps_hosts=" + ps_list + " " \
                + "--worker_hosts=" + workers_list + " " \
                + "--job_name=ps " \
                + "--task_id=" + str(index) + " " \
                + "--num_batches=30 --data_format=NCHW --display_every=2 --weak_scaling=true --parameter_server=cpu --device=gpu " \
                + " > /tmp/ps" + str(index) \
                + " 2>&1" \
                + " &" 
                
    script += "\n\n"

    script += "" \
                    + "python /tmp/tf_cnn_benchmarks.py " \
                    + "--model=inception3 " \
                    + "--batch_size=" + str(batch_size) + " " \
                    + "--ps_hosts=" + ps_list + " " \
                    + "--worker_hosts=" + workers_list + " " \
                    + "--job_name=worker " \
                    + "--task_id=" + str(index) + " "\
                    + "--num_batches=30 --data_format=NCHW --display_every=2 --weak_scaling=true --parameter_server=cpu --device=gpu " \
                    + "--num_gpus=" + str(gpu_per_node) + " " \
                    + " > /tmp/worker" + str(index) \
                    + " 2>&1" \
                    + " &"
                
    script += "\n\n"
    
    return script    


def get_script_name(model):
    return {
        'inceptionv3':'imagenet_distributed_train.py',
        'alexnet':'alexnet.py',
        'resnet':'resnet_dist.py',
    }.get(model, 'unknown-model')

def get_model_dir(model, remote_dir):
    suffix = {
        'inceptionv3':'inception/inception',
        'alexnet':'alexnet',
        'resnet':'resnet',
    }.get(model, 'unknown-model')
    return remote_dir + suffix;

def gen_scripts(model, nodes_file, remote_dir, gen_dir_rel, num_nodes, gpu_per_node, batch_size):
    nodes = get_nodes(nodes_file)
    nodes = nodes[:num_nodes]
    
    workers_list = get_worker_list(nodes, gpu_per_node)
    ps_list = get_ps_list(nodes)

    for index, host in enumerate(nodes):
        sys.stderr.write('%d %s\n' % (index, host))
        script = get_script(get_script_name(model), remote_dir, workers_list, ps_list, index, batch_size, gpu_per_node)
        sys.stderr.write('\n\n%s\n\n' % script)
        file_name = gen_dir_rel + "/" + str(index+1) + ".sh"
        with open(file_name, "w") as sh_file:
            sh_file.write(script)

def main(argv):

    try:
        opts, args = getopt.getopt(argv, "", ["model=","nodes=","remote_dir=","gen_dir=","num_nodes=","gpu_per_node=","batch_size="])
    except getopt.GetoptError:
        print("Incorrect args")
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == "--model":
            model = arg
        if opt == "--nodes":
            nodes_file = os.path.abspath(arg)
        if opt == "--remote_dir":
            remote_dir = arg
        elif opt == "--gen_dir":
            gen_dir = os.path.abspath(arg)
            gen_dir_rel = arg
        if opt == "--num_nodes":
            num_nodes = int(arg)
        elif opt == "--gpu_per_node":
            gpu_per_node = int(arg)
        elif opt == "--batch_size":
            batch_size = int(arg)
    
    if(remote_dir == None or gen_dir == None or num_nodes == None or gpu_per_node == None or batch_size == None or nodes_file == None or model == None):
        print("Incorrect args")
        sys.exit(2)
    
    script_name = get_script_name(model)
        
    gen_scripts(model, nodes_file, remote_dir, gen_dir_rel, num_nodes, gpu_per_node, batch_size)
    
    print(script_name)
    

if __name__ == "__main__":
    main(sys.argv[1:])
    
