import platform
import socket
import subprocess
from time import sleep

import dns.message
import dns.query

from DNSConfig import DNSConfigChecker
from NetworkInterfaces import NetworkInterfaces
from output import CLIOutputManager

PUBLIC_DNS_SERVERS = {
    "Google": ("8.8.8.8", "2001:4860:4860::8888"),
    "Cloudflare": ("1.1.1.1", "2606:4700:4700::1111"),
    "Quad9": ("9.9.9.9", "2620:fe::fe"),
    "OpenDNS": ("208.67.222.222", "2620:119:35::35"),
    "CleanBrowsing": ("185.228.168.9", "2a0d:2a00:1::"),
}

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

    @staticmethod
    def _get_service_name_from_interface(interface: str):
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

            service_name = IPv6Enabler._get_service_name_from_interface(interface)
            if not service_name:
                print(f"\033[31mFailed to get service name for interface {interface}\033[0m")
                print("\033[31mERROR: Cannot bounce interface without service name.\033[0m")
                return
            print("\033[36mBouncing interface to trigger IPv6 rebind...\033[0m")
            subprocess.check_call(["networksetup", "-setnetworkserviceenabled",
                                   service_name, "off"])
            subprocess.check_call(["networksetup", "-setnetworkserviceenabled",
                                   service_name, "on"])
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
            sleep(0.5)
        return (v4_success, v6_success)



def check_interface_ips():
    IPmap = netinfo.get_ip_list(active_interfaces, verbose=True)
    not_ipv6_capable = [iface for iface, (v4, v6) in IPmap.items() if v4 and not v6 and not iface.startswith("lo") and "tun" not in iface]
    if not_ipv6_capable:
        print("\033[36mWe can now add IPv6 to these interfaces: \033[0m")
        for iface in not_ipv6_capable:
            print(f"- {iface}")
        print("\033[36m\nShould we enable IPv6 support? This will cause your connection reboot "
              "(This will require admin privileges) (y/N)\033[0m")
        if input().strip().lower() not in ['y', 'yes', '1']:
            print("\033[31mExiting without changes.\033[0m")
            exit(0)
        else:
            print("\033[32mAttempting to enable IPv6 on interfaces.\033[0m")
            enabler = IPv6Enabler(not_ipv6_capable)
            results = enabler.enable_ipv6_on_all()

            for iface, result in results.items():
                status = "\033[32mOK\033[0m" if result["success"] else "\033[31mFAILED\033[0m"
                print(f"{status} {iface}: {result['message']}")
                sleep(1)
            check_interface_ips()
    else:
        print("\033[32mAll online interfaces already support IPv6!\033[0m")


def lookup_online_interfaces():
    IPmap = netinfo.get_ip_list(active_interfaces, verbose=False)
    online_interfaces = [(iface, (v4, v6)) for iface, (v4, v6) in IPmap.items() if v4 and "lo" not in iface]
    return online_interfaces


if __name__ == "__main__":
    CLIOutputManager.print_banner()

    CLIOutputManager.print_phase_1()

    CLIOutputManager.print_checking_interfaces()
    netinfo = NetworkInterfaces()
    active_interfaces = netinfo.list_active_interfaces(verbose=True)

    if not active_interfaces:
        CLIOutputManager.print_no_active_interfaces()
        exit(1)

    # check which have internet access
    CLIOutputManager.print_ipv6_intro()
    check_interface_ips()
    online_interfaces = lookup_online_interfaces()

    # Begin DHCP Check
    if not online_interfaces:
        CLIOutputManager.print_no_active_interfaces()
        exit(1)

    CLIOutputManager.print_phase_2()

    print("\033[36mChecking your DNS configurations\033[0m")
    dns_checker = DNSConfigChecker(online_interfaces, netinfo)
    resolvers = dns_checker.get_resolvers()
    for resolver in resolvers:
        CLIOutputManager.print_resolver_status(resolver)
    CLIOutputManager.print_phase_3()

