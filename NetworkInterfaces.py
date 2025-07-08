import socket

from psutil import net_if_stats, net_if_addrs

from output import CLIOutputManager


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

    def get_ip(self, interface_name, family=socket.AF_INET, allow_loopback=True):
        addrs = self.interfaces_addrs.get(interface_name)
        if not addrs:
            return None

        link_local = None

        for addr in addrs:
            if addr.family == family:
                ip = addr.address.split('%')[0]

                if family == socket.AF_INET6:
                    if ip == "::1" and not allow_loopback:
                        continue
                    if ip.startswith("fe80"):
                        link_local = ip
                        continue
                    return ip  # return global or loopback IPv6
                else:
                    return ip  # return IPv4

        return link_local if family == socket.AF_INET6 else None

    def get_ip_list(self, interfaces, verbose=False):
        ip_list = {}
        for iface, stats in interfaces:
            v4_ip = self.get_ip(iface, socket.AF_INET)
            v6_ip = self.get_ip(iface, socket.AF_INET6)
            if verbose:
                CLIOutputManager.print_interface_status(iface, v4_ip, v6_ip)
            ip_list[iface] = (v4_ip, v6_ip)
        return ip_list