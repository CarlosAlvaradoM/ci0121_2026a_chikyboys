//P4_16
/*
 * Proyecto Final - Etapa 3: Redes Programables con P4
 * Opcion A: Cache DNS en el Data Plane
 */

#include <core.p4>
#include <v1model.p4>

typedef bit<9> egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

const bit<16> TYPE_IPV4 = 0x0800;
const bit<8> PROTO_UDP = 0x11;
const bit<16> DNS_PORT = 53;
const bit<32> CACHE_SIZE = 1024;


//Headers
header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16> etherType;
}

header ipv4_t {
    bit<4> version;
    bit<4> ihl;
    bit<8> diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3> flags;
    bit<13> fragOffset;
    bit<8> ttl;
    bit<8> protocol;
    bit<16> hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> length_;
    bit<16> checksum;
}

// Cabecera "tipo DNS" simplificada (44 bytes)
// trans_id : identificador de transaccion (igual que DNS real)
// flags : bit0 = QR (0=consulta, 1=respuesta)
// qtype : 1 = registro tipo A (unico tipo soportado)
// qname : nombre de dominio ASCII, rellenado con 0x00, max 32 bytes
// answer_ip : IPv4 resuelta (0 en consultas)
// ttl : segundos de validez de la respuesta
header dns_t {
    bit<16> trans_id;
    bit<8> flags;
    bit<8> qtype;
    bit<256> qname;
    bit<32> answer_ip;
    bit<32> ttl;
}

struct headers {
    ethernet_t ethernet;
    ipv4_t ipv4;
    udp_t udp;
    dns_t dns;
}

struct metadata {
    bit<32> cache_index;
}


//Parser
parser MyParser(packet_in packet, out headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            PROTO_UDP: parse_udp;
            default: accept;
        }
    }

    state parse_udp {
        packet.extract(hdr.udp);
        transition select(hdr.udp.dstPort, hdr.udp.srcPort) {
            (DNS_PORT, _): parse_dns;
            (_, DNS_PORT): parse_dns;
            default: accept;
        }
    }

    state parse_dns {
        packet.extract(hdr.dns);
        transition accept;
    }
}



//Checksum verification
control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}


//Ingress Processing
control MyIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {

    // Registers: la cache vive en el data plane 
    register<bit<1>>(CACHE_SIZE) reg_valid;  // 1 si la entrada esta ocupada
    register<bit<256>>(CACHE_SIZE) reg_qname;  // nombre de dominio cacheado
    register<bit<32>>(CACHE_SIZE) reg_ip;  // IP cacheada
    register<bit<32>>(CACHE_SIZE) reg_ttl;  // TTL cacheado
    register<bit<32>>(1) reg_hits;  // contador global de hits
    register<bit<32>>(1) reg_misses;  // contador global de misses

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        standard_metadata.egress_spec = port;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    table ipv4_lpm {
        key = { hdr.ipv4.dstAddr: lpm; }
        actions = { ipv4_forward; drop; NoAction; }
        size = 1024;
        default_action = NoAction();
    }

    action compute_index() {
        hash(meta.cache_index, HashAlgorithm.crc32, (bit<32>)0,
             { hdr.dns.qname }, CACHE_SIZE);
    }

    action send_cached_answer() {
        bit<32> cached_ip;
        bit<32> cached_ttl;
        reg_ip.read(cached_ip, meta.cache_index);
        reg_ttl.read(cached_ttl, meta.cache_index);

        hdr.dns.flags = hdr.dns.flags | 0x1;  // QR = 1 (respuesta)
        hdr.dns.answer_ip = cached_ip;
        hdr.dns.ttl = cached_ttl;

        // Intercambiar direcciones para que el paquete vuelva al cliente
        macAddr_t tmpMac = hdr.ethernet.srcAddr;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = tmpMac;

        ip4Addr_t tmpIp = hdr.ipv4.srcAddr;
        hdr.ipv4.srcAddr = hdr.ipv4.dstAddr;
        hdr.ipv4.dstAddr = tmpIp;

        bit<16> tmpPort = hdr.udp.srcPort;
        hdr.udp.srcPort = hdr.udp.dstPort;
        hdr.udp.dstPort = tmpPort;
        hdr.udp.checksum = 0;  // deshabilitar checksum UDP (valido en IPv4)

        standard_metadata.egress_spec = standard_metadata.ingress_port;

        bit<32> h;
        reg_hits.read(h, 0);
        h = h + 1;
        reg_hits.write(0, h);
    }

    action count_miss() {
        bit<32> m;
        reg_misses.read(m, 0);
        m = m + 1;
        reg_misses.write(0, m);
    }

    action update_cache() {
        reg_valid.write(meta.cache_index, 1);
        reg_qname.write(meta.cache_index, hdr.dns.qname);
        reg_ip.write(meta.cache_index, hdr.dns.answer_ip);
        reg_ttl.write(meta.cache_index, hdr.dns.ttl);
    }

    apply {
        if (hdr.dns.isValid()) {
            compute_index();
            bit<1> qr = (bit<1>)(hdr.dns.flags & 0x1);

            if (qr == 0) {
                // Es una CONSULTA
                bit<1>   valid;
                bit<256> stored_name;
                reg_valid.read(valid, meta.cache_index);
                reg_qname.read(stored_name, meta.cache_index);

                if (valid == 1 && stored_name == hdr.dns.qname) {
                    send_cached_answer();  // HIT
                } else {
                    count_miss();  // MISS
                    ipv4_lpm.apply();
                }
            } else {
                // Es una RESPUESTA que viene del servidor DNS real
                update_cache();
                ipv4_lpm.apply();
            }
        } else if (hdr.ipv4.isValid()) {
            ipv4_lpm.apply();
        }
    }
}


//Egress Processing
control MyEgress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    apply { }
}

//Checksum Computation
control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
        update_checksum(
            hdr.ipv4.isValid(),
            { hdr.ipv4.version, hdr.ipv4.ihl, hdr.ipv4.diffserv,
              hdr.ipv4.totalLen, hdr.ipv4.identification, hdr.ipv4.flags,
              hdr.ipv4.fragOffset, hdr.ipv4.ttl, hdr.ipv4.protocol,
              hdr.ipv4.srcAddr, hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum, HashAlgorithm.csum16);
    }
}


//Deparser
control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.udp);
        packet.emit(hdr.dns);
    }
}


//Switch
V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
