import re
import subprocess
from ipaddress import ip_address

from NetworkInterfaces import NetworkInterfaces


class Resolver:
    SOURCE_PRIORITY = {
        "Custom": 0,
        "VPN Tunnel Provided": 1,
        "Likely DHCP provisioned": 2,
        "VPN Intercepted": 3,
        "Unknown": 4,
    }

    def __init__(self, interface: str, ip: str, source: str, isActive: bool = True):
        self.interface = interface
        self.ip = ip
        self.source = source
        self.isActive = isActive

    def __repr__(self):
        return f"Resolver(interface='{self.interface}', ip='{self.ip}', source='{self.source}')"

    def sort_key(self):
        if self.ip.lower() == "unknown":
            ip_key = ip_address("255.255.255.255")
        else:
            ip_key = ip_address(self.ip)
        return (
            self.interface,
            Resolver.SOURCE_PRIORITY.get(self.source, 99),
            ip_key
        )

    @staticmethod
    def sort_resolvers(resolvers):
        return sorted(resolvers, key=lambda r: r.sort_key())

class DNSConfigChecker:
    def __init__(self, interfaces, netinfo: NetworkInterfaces):
        self.interfaces = interfaces
        self.netinfo = netinfo

    def get_resolvers(self):
        # Check CUSTOM resolvers (networksetup)
        service_to_interface = self._get_service_to_interface_map()
        interface_to_service = self._get_interface_to_service_map()
        custom_resolvers = []
        for interface in self.interfaces:
            service = interface_to_service.get(interface[0], None)
            if service:
                try:
                    output = subprocess.check_output(["networksetup", "-getdnsservers", service], text=True).strip()
                    if output and "aren't" not in output:
                        for ip in output.splitlines():
                            custom_resolvers.append(Resolver(interface[0], ip.strip(), "Custom"))
                except subprocess.CalledProcessError:
                    continue

        dhcp_resolvers = []

        #check DHCP resolvers (ipconfig)
        for interface in self.interfaces:
            try:
                output = subprocess.check_output(["ipconfig", "getpacket", interface[0]], text=True).strip()
                if "domain_name_server" in output:
                    for line in output.splitlines():
                        if "domain_name_server" in line:
                            ip = line.split(":")[1].strip()
                            ip = ip[1:-1]
                            ips = ip.split(", ")
                            for ip in ips:
                                if ip:
                                    dhcp_resolvers.append(Resolver(interface[0],ip, "Likely DHCP provisioned"))
            except subprocess.CalledProcessError:
                continue

        # search for VPN provided (Scoped+utun/tun, scutil)
        vpn_resolvers = []
        try:
            output = subprocess.check_output(["scutil", "--dns"], text=True).strip()
            output = output.split("DNS configuration (for scoped queries)")[1].strip()
            resolvers = re.split(r"^\s*resolver #\d+\s*$", output, flags=re.MULTILINE)[1:]
            for resolver in resolvers:
                interface = None
                ips = []
                if "if_index" in resolver and "nameserver" in resolver:
                    lines = resolver.splitlines()

                    for line in lines:
                        if "if_index" in line:
                            interface = ((line.split(":")[1]).split(" ")[2])[1:-1]
                        elif "nameserver" in line:
                            ip = line.split(":")[1].strip()
                            if ip:
                                ips.append(ip.strip())

                if interface and ips and "tun" in interface:
                    for ip in ips:
                        vpn_resolvers.append(Resolver(interface, ip, "VPN Tunnel Provided"))

        except subprocess.CalledProcessError:
            pass
        # Search for utun interfaces without DNS provided (VPN Intercepted)
        for interface in self.interfaces:
            if "tun" in interface[0]:
                try:
                    output = subprocess.check_output(["scutil", "--dns"], text=True).strip()
                    if interface[0] in output:
                        continue
                    vpn_resolvers.append(Resolver(interface[0], "Unknown", "VPN Intercepted"))
                except subprocess.CalledProcessError:
                    continue

        result = custom_resolvers + dhcp_resolvers + vpn_resolvers

        OVERRIDE_PRIORITY = {
            "Custom": 3,
            "VPN Tunnel Provided": 2,
            "Likely DHCP provisioned": 1,
            "VPN Intercepted": 0,
        }

        best_scores = {}
        for resolver in result:
            iface = resolver.interface
            iface
            if iface not in best_scores:
                best_scores[iface] = OVERRIDE_PRIORITY[resolver.source]
            else:
                best_scores[iface] = max(best_scores[iface], OVERRIDE_PRIORITY[resolver.source])
        for resolver in result:
            if resolver.interface in best_scores:
                if OVERRIDE_PRIORITY[resolver.source] < best_scores[resolver.interface]:
                    resolver.isActive = False
                else:
                    resolver.isActive = True




        return Resolver.sort_resolvers(result)

    def _get_service_to_interface_map(self):
        output = subprocess.check_output(["networksetup", "-listallhardwareports"], text=True)
        entries = output.strip().split("\n\n")
        service_to_interface = {}

        for entry in entries:
            lines = entry.strip().splitlines()
            port = None
            device = None
            for line in lines:
                if line.startswith("Hardware Port"):
                    port = line.split(":")[1].strip()
                elif line.startswith("Device"):
                    device = line.split(":")[1].strip()
            if port and device:
                service_to_interface[port] = device

        return service_to_interface

    def _get_interface_to_service_map(self):
        HARDCODED_IFACE_TO_SERVICE = {
            "en0": "Wi-Fi",
            "utun4": "AdGuard VPN",
            "utun5": "WireGuard",
            "bridge0": "VM Bridge",
            "lo0": "Loopback",
            # Add others as needed
        }
        return HARDCODED_IFACE_TO_SERVICE