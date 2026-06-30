#include <core.p4>
#include <v1model.p4>

header ethernet_t {
    bit<48> dstAddr;
    bit<48> srcAddr;
    bit<16> etherType;
}

header ipv4_t {
    bit<4>  version;
    bit<4>  ihl;
    bit<8>  diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3>  flags;
    bit<13> fragOffset;
    bit<8>  ttl;
    bit<8>  protocol;
    bit<16> hdrChecksum;
    bit<32> srcAddr;
    bit<32> dstAddr;
}

struct metadata_t {
    bit<32> flow_hash;
}

struct digest_t {
    bit<32> srcAddr;
    bit<32> dstAddr;
}

struct headers_t {
    ethernet_t ethernet;
    ipv4_t     ipv4;
}

counter(4, CounterType.packets_and_bytes) proto_counter;

register<bit<32>>(1024) flow_byte_count;

parser MyParser(packet_in pkt,
                out headers_t hdr,
                inout metadata_t meta,
                inout standard_metadata_t std_meta) {
    state start {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            0x0800: parse_ipv4;
            default: accept;
        }
    }
    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition accept;
    }
}

control MyVerifyChecksum(inout headers_t hdr, inout metadata_t meta) {
    apply {}
}

control MyIngress(inout headers_t hdr,
                  inout metadata_t meta,
                  inout standard_metadata_t std_meta) {

    direct_counter(CounterType.packets_and_bytes) flow_counter;

    register<bit<32>>(1) elephant_threshold;
    register<bit<1>>(1024) elephant_flag;

    action count_and_forward() {
        // accion para flujos YA conocidos (entrada real en la tabla)
        // el direct counter se incrementa automaticamente aqui
    }

    action learn_flow() {
        // accion para flujos NUEVOS (miss): notifica al control plane
        digest<digest_t>(1, { hdr.ipv4.srcAddr, hdr.ipv4.dstAddr });
    }

    action drop() {
        mark_to_drop(std_meta);
    }

    table flow_stats {
        key = {
            hdr.ipv4.srcAddr: exact;
            hdr.ipv4.dstAddr: exact;
        }
        actions        = { count_and_forward; drop; }
        default_action = count_and_forward();
        counters       = flow_counter;
        size           = 1024;
    }

    apply {
        if (hdr.ipv4.isValid()) {

            if (hdr.ipv4.protocol == 6) {
                proto_counter.count(0);
            } else if (hdr.ipv4.protocol == 17) {
                proto_counter.count(1);
            } else if (hdr.ipv4.protocol == 1) {
                proto_counter.count(2);
            } else {
                proto_counter.count(3);
            }

            hash(meta.flow_hash, HashAlgorithm.crc32,
                 (bit<32>)0, { hdr.ipv4.srcAddr, hdr.ipv4.dstAddr },
                 (bit<32>)1024);

            bit<32> current_bytes;
            flow_byte_count.read(current_bytes, meta.flow_hash);
            current_bytes = current_bytes + (bit<32>)std_meta.packet_length;
            flow_byte_count.write(meta.flow_hash, current_bytes);

            bit<32> threshold;
            elephant_threshold.read(threshold, 0);
            if (current_bytes > threshold) {
                elephant_flag.write(meta.flow_hash, 1);
            }

            flow_stats.apply();

            std_meta.egress_spec = 2;
        }
    }
}

control MyEgress(inout headers_t hdr,
                 inout metadata_t meta,
                 inout standard_metadata_t std_meta) {
    apply {}
}

control MyComputeChecksum(inout headers_t hdr, inout metadata_t meta) {
    apply {}
}

control MyDeparser(packet_out pkt, in headers_t hdr) {
    apply {
        pkt.emit(hdr.ethernet);
        pkt.emit(hdr.ipv4);
    }
}

V1Switch(MyParser(), MyVerifyChecksum(), MyIngress(), MyEgress(),
         MyComputeChecksum(), MyDeparser()) main;
