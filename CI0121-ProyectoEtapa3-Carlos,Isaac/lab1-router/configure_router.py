import subprocess

def add_rule(thrift_port, ip_prefix, prefix_len, dst_mac, src_mac, port):
    cmd = "table_add ipv4_lpm ipv4_forward {}/{} => {} {} {}\n".format(
        ip_prefix, prefix_len, dst_mac, src_mac, port)
    p = subprocess.Popen(
        ['simple_switch_CLI', '--thrift-port', str(thrift_port)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = p.communicate(cmd.encode())
    print(out.decode())

if __name__ == '__main__':
    S1_TO_H1 = '00:00:00:01:01:01'
    S1_TO_S2 = '00:00:00:01:02:01'

    S2_TO_H2 = '00:00:00:02:02:01'
    S2_TO_S1 = '00:00:00:02:01:01'
    S2_TO_S3 = '00:00:00:02:03:01'

    S3_TO_H3 = '00:00:00:03:01:01'
    S3_TO_H4 = '00:00:00:03:02:01'
    S3_TO_S2 = '00:00:00:03:03:01'

    H1_MAC = '00:00:00:00:01:01'
    H2_MAC = '00:00:00:00:02:01'
    H3_MAC = '00:00:00:00:03:01'
    H4_MAC = '00:00:00:00:04:01'

    add_rule(9090, '10.0.1.0', 24, H1_MAC,    S1_TO_H1, 1)
    add_rule(9090, '10.0.2.0', 24, S2_TO_S1,  S1_TO_S2, 2)
    add_rule(9090, '10.0.3.0', 24, S2_TO_S1,  S1_TO_S2, 2)
    add_rule(9090, '10.0.4.0', 24, S2_TO_S1,  S1_TO_S2, 2)

    add_rule(9091, '10.0.1.0', 24, S1_TO_S2,  S2_TO_S1, 2)
    add_rule(9091, '10.0.2.0', 24, H2_MAC,    S2_TO_H2, 1)
    add_rule(9091, '10.0.3.0', 24, S3_TO_S2,  S2_TO_S3, 3)
    add_rule(9091, '10.0.4.0', 24, S3_TO_S2,  S2_TO_S3, 3)

    add_rule(9092, '10.0.1.0', 24, S2_TO_S3,  S3_TO_S2, 3)
    add_rule(9092, '10.0.2.0', 24, S2_TO_S3,  S3_TO_S2, 3)
    add_rule(9092, '10.0.3.0', 24, H3_MAC,    S3_TO_H3, 1)
    add_rule(9092, '10.0.4.0', 24, H4_MAC,    S3_TO_H4, 2)

    print("Tablas configuradas.")
