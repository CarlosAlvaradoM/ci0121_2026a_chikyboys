import subprocess

HOSTS = ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4']

def add_flow(thrift_port, src_ip, dst_ip):
    cmd = f"table_add flow_stats count_and_forward {src_ip} {dst_ip} =>\n"
    p = subprocess.Popen(
        ['simple_switch_CLI', '--thrift-port', str(thrift_port)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, _ = p.communicate(cmd.encode())
    print(out.decode().strip().splitlines()[-1] if out else "")

if __name__ == '__main__':
    for src in HOSTS:
        for dst in HOSTS:
            if src != dst:
                add_flow(9090, src, dst)
    print("Flujos pre-instalados (todos los pares posibles entre 4 hosts).")
