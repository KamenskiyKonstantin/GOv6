import socket
from time import sleep
import dns.message
import dns.query
from psutil import net_if_stats, net_if_addrs

from output import CLIOutputManager

PUBLIC_DNS_SERVERS = {
    "Google": ("8.8.8.8", "2001:4860:4860::8888"),
    "Cloudflare": ("1.1.1.1", "2606:4700:4700::1111"),
    "Quad9": ("9.9.9.9", "2620:fe::fe"),
    "OpenDNS": ("208.67.222.222", "2620:119:35::35"),
    "CleanBrowsing": ("185.228.168.9", "2a0d:2a00:1::"),
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


import subprocess
import platform
import socket


class IPv6Enabler:
    def __init__(self, interfaces: list[str]):
        self.interfaces = interfaces
        self.system = platform.system()

    def enable_ipv6_on_all(self):
        results = {}
        for iface in self.interfaces:
            success, message = self._enable_ipv6(iface)
            results[iface] = {
                "success": success,
                "message": message
            }
        return results

    def _enable_ipv6(self, interface: str):
        if self.system == "Darwin":
            results = self._enable_ipv6_mac(interface)
            self.bounce_interface_mac(interface)

            return results

        elif self.system == "Linux":
            return self._enable_ipv6_linux(interface)
        else:
            return False, f"Unsupported OS: {self.system}"

    def _enable_ipv6_mac(self, interface: str):
        service = self._get_service_name_from_interface(interface)
        if not service:
            return False, f"Could not resolve network service name for interface '{interface}'"

        try:
            subprocess.check_call(["networksetup", "-setv6automatic", service])
            return True, f"IPv6 enabled on interface '{interface}' via service '{service}'"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to enable IPv6 on '{service}' ({interface}): {e}"
        except FileNotFoundError:
            return False, "networksetup command not found"

    def _get_service_name_from_interface(self, interface: str):
        try:
            output = subprocess.check_output(["networksetup", "-listallhardwareports"]).decode()
            blocks = output.strip().split("\n\n")
            for block in blocks:
                lines = block.splitlines()
                if any(f"Device: {interface}" in line for line in lines):
                    for line in lines:
                        if line.startswith("Hardware Port:"):
                            return line.split(":")[1].strip()
            return None
        except subprocess.CalledProcessError:
            return None

    def _enable_ipv6_linux(self, interface: str):
        try:
            subprocess.check_call(["sudo", "sysctl", f"net.ipv6.conf.{interface}.disable_ipv6=0"])
            return True, f"IPv6 enabled on {interface} (Linux)"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to enable IPv6 on {interface}: {e}"
        except FileNotFoundError:
            return False, "sysctl command not found"

    @staticmethod
    def bounce_interface_mac(interface):
        try:
            subprocess.check_call(["sudo", "-S", "ifconfig", interface, "down", ])
            subprocess.check_call(["sudo", "-S", " ifconfig", interface, "up", ])
            return True, f"Bounced interface {interface} to trigger IPv6 rebind"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to bounce interface {interface}: {e}"


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
        v4_success, v6_success = [], []
        for dns_name, (v4_ip, v6_ip) in dns_servers.items():
            v4_result = self.dig_over_interface(v4_ip, record_type="A")
            v6_result = self.dig_over_interface(v6_ip, record_type="AAAA")

            if v4_result['success']:
                v4_success.append((dns_name, v4_result['answers']))
            if v6_result['success']:
                v6_success.append((dns_name, v6_result['answers']))

            if verbose:
                print(
                    dns_name.ljust(22),
                    "\033[32m|  DNSv4 Reachable  |\033[0m" if v4_result['success']
                    else f"\033[31m| DNSv4 Unreachable | ERROR: {v4_result.get('error', '')} |\033[0m",

                    "\033[32m|  DNSv6 Reachable  |\033[0m" if v6_result['success']
                    else f"\033[31m| DNSv6 Unreachable | ERROR: {v6_result.get('error', '')} |\033[0m",
                )
        return (v4_success, v6_success)


if __name__ == "__main__":
    print("GOv6 - IPv6 Switch Toolkit")
    print("Listing active network interfaces:")
    netinfo = NetworkInterfaces()
    active_interfaces = netinfo.list_active_interfaces(verbose=True)

    DNSv6_reachable = []
    DNSv4_reachable = []
    has_enabled_flag = False

    while not DNSv6_reachable:
        print("\nChecking DNS connectivity on active interfaces:\n")
        for iface_name, _ in active_interfaces:
            print(f"Checking public DNS servers for interface: {iface_name}")
            probe = DNSProbe(iface_name, netinfo)
            DNSv4, DNSv6 = probe.check_dns_connectivity(PUBLIC_DNS_SERVERS, verbose=True)

            if DNSv4:
                DNSv4_reachable.append(iface_name)
                CLIOutputManager.print_ipv4_success()

            if not DNSv6:
                CLIOutputManager.show_interface_down_warning()
            else:
                DNSv6_reachable.append(iface_name)
                CLIOutputManager.print_ipv6_success()

        if not DNSv6_reachable:
            CLIOutputManager.show_all_interfaces_failure()
            if not DNSv4_reachable:
                CLIOutputManager.print_ipv4_missing()
                exit(1)

            CLIOutputManager.print_ipv6_enable_failed_message()
            CLIOutputManager.prompt_ipv6_enable()
            user_input = input().strip().lower()
            if user_input == 'y':
                CLIOutputManager.print_ipv6_attempting_enable()
                enabler = IPv6Enabler(DNSv4_reachable)
                results = enabler.enable_ipv6_on_all()

                for iface, result in results.items():
                    status = "\033[32mOK\033[0m" if result["success"] else "\033[31mFAILED\033[0m"
                    if result["success"]:
                        has_enabled_flag = True
                    print(f"{status} {iface}: {result['message']}")
                    sleep(1)

            else:
                CLIOutputManager.print_ipv6_skipped()
                exit(1)
        else:
            CLIOutputManager.show_all_interfaces_success(DNSv6_reachable)