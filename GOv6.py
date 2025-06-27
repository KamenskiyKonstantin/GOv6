from psutil import net_if_stats, net_if_addrs
import socket
import dns.message
import dns.query


PUBLIC_DNS_SERVERS = {
    "GOOGLE 1": ("8.8.8.8", "2001:4860:4860::8888"),
    "GOOGLE 2": ("8.8.4.4", "2001:4860:4860::8844"),
    "CLOUDFLARE 1": ("1.1.1.1", "2606:4700:4700::1111"),
    "CLOUDFLARE 2": ("1.0.0.1", "2606:4700:4700::1001"),
    "QUAD9 1": ("9.9.9.9", "2620:fe::fe"),
    "QUAD9 2": ("149.112.112.112", "2620:fe::9"),
    "OPENDNS 1": ("208.67.222.222", "2620:119:35::35"),
    "OPENDNS 2": ("208.67.220.220", "2620:119:53::53"),
    "CLEANBROWSING FAMILY": ("185.228.168.9", "2a0d:2a00:1::"),
    "CLEANBROWSING ADULT": ("185.228.168.10", "2a0d:2a00:2::"),
}


class NetworkInterfaces:
    def __init__(self):
        self.interfaces_stats = net_if_stats()
        self.interfaces_addrs = net_if_addrs()

    def list_active_interfaces(self, verbose=True):
        active = []
        for iface, stats in self.interfaces_stats.items():
            if stats.isup:
                active.append((iface, stats))
            if verbose:
                status = "\033[32m| ONLINE |\033[0m" if stats.isup else "\033[31m| OFFLINE |\033[0m"
                print(f"Interface: {iface}".ljust(30), status)
        return active

    def get_ip(self, interface_name, family=socket.AF_INET):
        addrs = self.interfaces_addrs.get(interface_name)
        if not addrs:
            return None
        for addr in addrs:
            if addr.family == family:
                return addr.address.split('%')[0]  # Strip zone index if present
        return None


class DNSProbe:
    def __init__(self, interface_name: str, netinfo: NetworkInterfaces, timeout=2):
        self.interface_name = interface_name
        self.netinfo = netinfo
        self.timeout = timeout
        self.v4_ip = self.netinfo.get_ip(interface_name, socket.AF_INET)
        self.v6_ip = self.netinfo.get_ip(interface_name, socket.AF_INET6)

    def dig_over_interface(self, dns_ip, record_type="AAAA"):
        family = socket.AF_INET6 if ':' in dns_ip else socket.AF_INET
        local_ip = self.v6_ip if family == socket.AF_INET6 else self.v4_ip

        if not local_ip:
            return {
                "success": False,
                "error": f"No {'IPv6' if family == socket.AF_INET6 else 'IPv4'} address for interface {self.interface_name}"
            }

        try:
            query = dns.message.make_query("google.com", record_type)
            sock = socket.socket(family, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            sock.bind((local_ip, 0))  # Bind to interface's IP address
            response = dns.query.udp(query, dns_ip, timeout=self.timeout, sock=sock)
            sock.close()

            answers = response.answer
            if answers:
                return {
                    "success": True,
                    "answers": [str(rr) for section in answers for rr in section.items]
                }
            else:
                return {"success": False, "error": "No DNS answers"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_dns_connectivity(self, dns_servers: dict, verbose=True):
        results = []
        for dns_name, (v4_ip, v6_ip) in dns_servers.items():
            v4_result = self.dig_over_interface(v4_ip, record_type="A")
            v6_result = self.dig_over_interface(v6_ip, record_type="AAAA")

            results.append({
                "dns_name": dns_name,
                "dns_v4": v4_result,
                "dns_v6": v6_result,
            })

            if verbose:
                print(
                    dns_name.ljust(22),
                    "\033[32m|  DNSv4 Reachable  |\033[0m" if v4_result['success']
                    else f"\033[31m| DNSv4 Unreachable | ERROR: {v4_result.get('error','')} |\033[0m",

                    "\033[32m|  DNSv6 Reachable  |\033[0m" if v6_result['success']
                    else f"\033[31m| DNSv6 Unreachable | ERROR: {v6_result.get('error','')} |\033[0m",
                )
        return results



if __name__ == "__main__":
    print("GOv6 - IPv6 Switch Toolkit")
    print("Listing active network interfaces:")
    netinfo = NetworkInterfaces()
    active_interfaces = netinfo.list_active_interfaces(verbose=True)

    print("\nChecking DNS connectivity on active interfaces:\n")
    for iface_name, _ in active_interfaces:
        print(f"Checking public DNS servers for interface: {iface_name}")
        probe = DNSProbe(iface_name, netinfo)
        probe.check_dns_connectivity(PUBLIC_DNS_SERVERS, verbose=True)
        print()