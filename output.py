DNS_PROVIDERS = {
    # Google DNS
    "8.8.8.8": "Google",
    "8.8.4.4": "Google",
    "2001:4860:4860::8888": "Google",
    "2001:4860:4860::8844": "Google",

    # Cloudflare DNS
    "1.1.1.1": "Cloudflare",
    "1.0.0.1": "Cloudflare",
    "2606:4700:4700::1111": "Cloudflare",
    "2606:4700:4700::1001": "Cloudflare",

    # Quad9 DNS
    "9.9.9.9": "Quad9",
    "149.112.112.112": "Quad9",
    "2620:fe::fe": "Quad9",
    "2620:fe::9": "Quad9",

    # OpenDNS
    "208.67.222.222": "OpenDNS",
    "208.67.220.220": "OpenDNS",
    "2620:119:35::35": "OpenDNS",
    "2620:119:53::53": "OpenDNS",

    # CleanBrowsing
    "185.228.168.9": "CleanBrowsing",
    "185.228.169.9": "CleanBrowsing",
    "2a0d:2a00:1::2": "CleanBrowsing",
    "2a0d:2a00:2::2": "CleanBrowsing",
}


def nameserver_to_provider(ns):
    if ns in DNS_PROVIDERS:
        return DNS_PROVIDERS[ns]
    return "Unknown provider"


class CLIOutputManager:
    @staticmethod
    def color(text: str, code: str = "0") -> str:
        return f"\033[{code}m{text}\033[0m"

    @staticmethod
    def _box(lines: list[str], color_code: str = "0") -> str:
        width = 60
        top = "+" + "-" * width + "+"
        content = [f"|{line.center(width)}|" for line in lines]
        bottom = "+" + "-" * width + "+"
        return CLIOutputManager.color("\n".join([top] + content + [bottom]), color_code)

    @staticmethod
    def print_banner():
        print(CLIOutputManager.color("GOv6 - IPv6 Switch Toolkit", "36"))

    @staticmethod
    def print_checking_interfaces():
        print(CLIOutputManager.color("Let's see what network interfaces your computer has", "36"))

    @staticmethod
    def print_no_active_interfaces():
        print(CLIOutputManager.color("ERROR: No active network interfaces found.", "31"))
        print(CLIOutputManager.color("Please check your network connections.", "31"))

    @staticmethod
    def print_ipv6_intro():
        print(CLIOutputManager.color("\nNow let us see if your computer already supports IPv6\n", "36"))

    @staticmethod
    def print_checking_dns_banner():
        print(CLIOutputManager.color("\nChecking DNS connectivity on active interfaces:\n", "36"))

    @staticmethod
    def print_checking_interface_dns(iface_name):
        print(CLIOutputManager.color(f"Checking public DNS servers for interface: {iface_name}", "36"))

    @staticmethod
    def show_interface_down_warning():
        lines = [
            "WARNING: No DNSv6 servers reachable",
            "on this interface.",
            "",
            "Please check your IPv6 configuration and DNS setup.",
            "IPv6 resolution will not work until this is resolved."
        ]
        print(CLIOutputManager._box(lines, "33"))

    @staticmethod
    def show_all_interfaces_failure():
        lines = [
            "ERROR: No DNSv6 servers reachable on any active interface",
            "",
            "Please ensure your network configuration supports IPv6",
            "and that DNS servers are correctly configured."
        ]
        print(CLIOutputManager._box(lines, "31"))

    @staticmethod
    def show_all_interfaces_success(ifaces):
        lines = [
            "SUCCESS: DNSv6 servers reachable on these interfaces:",
            ""
        ]
        has_physical_IPv6 = False
        iface_lines = []

        for iface in ifaces:
            if iface.startswith("en") or iface.startswith("eth"):
                has_physical_IPv6 = True
            line = f"- {iface}"
            if iface.startswith("utun") or iface.startswith("tun"):
                line += " (VPN tunnel)"
            elif iface.startswith("lo"):
                line += " (Loopback)"
            elif iface.startswith("bridge"):
                line += " (VM Bridge)"
            iface_lines.append(line)

        print(CLIOutputManager._box(lines + iface_lines, "32"))

        if not has_physical_IPv6:
            print(CLIOutputManager.color("No physical interfaces with reachable IPv6 found.", "31"))
            print(CLIOutputManager.color("Disable VPNs or bridges to test native IPv6.", "31"))
        print()

    @staticmethod
    def prompt_ipv6_enable():
        print(CLIOutputManager.color("Should we attempt enabling IPv6 on IPv4 interfaces? (y/N)", "32"))

    @staticmethod
    def print_ipv4_success():
        print(CLIOutputManager.color("Some DNS servers reachable via IPv4 on this interface.", "33"))

    @staticmethod
    def print_ipv6_success():
        print(CLIOutputManager.color("Some DNS servers reachable via IPv6 on this interface.", "32"))

    @staticmethod
    def print_ipv6_attempting_enable():
        print(CLIOutputManager.color("Attempting to enable IPv6 on IPv4 interfaces...", "32"))

    @staticmethod
    def print_ipv6_skipped():
        print(CLIOutputManager.color("Skipping IPv6 enabling on IPv4 interfaces.", "31"))
        print(CLIOutputManager.color("Please check your network configuration manually.", "31"))

    @staticmethod
    def print_ipv6_enable_failed_message():
        print(CLIOutputManager.color(
            "Since enabling IPv6 did not help, your network likely does not currently support IPv6.\n"
            "Please contact your network administrator to enable it.", "31"))

    @staticmethod
    def print_interface_status(interface: str, ipv4: str = None, ipv6: str = None):
        def classify_ipv6(ip: str) -> str:
            if not ip:
                return "none"
            if ip == "::1":
                return "loopback"
            if ip.startswith("fe80"):
                return "link-local"
            if ip.startswith("fd"):
                return "unique-local"
            if ip.startswith("2") or ip.startswith("3"):
                return "global"
            return "other"

        def describe_interface(ifname: str, scope: str) -> str:
            if ifname.startswith("utun") or ifname.startswith("tun"):
                return "Virtual VPN tunnel"
            if ifname.startswith("en"):
                return "Physical Ethernet/Wi-Fi interface"
            if ifname.startswith("lo"):
                return "Loopback (local-only) interface"
            if ifname.startswith("bridge"):
                return "Virtual bridge interface"
            if ifname.startswith("awdl"):
                return "Apple Wireless Direct Link (peer mesh)"
            if ifname.startswith("llw"):
                return "Low-latency Wi-Fi (Apple-specific)"
            if ifname.startswith("anpi"):
                return "Thunderbolt adapter or aux interface"
            return "Unknown or system-specific interface"

        ipv4_display = f"IPv4: {ipv4}" if ipv4 else "IPv4: NONE"
        ipv4_str = CLIOutputManager.color(f"| {ipv4_display.ljust(20)} |", "32" if ipv4 else "31")

        ipv6_scope = classify_ipv6(ipv6)
        if ipv6_scope == "global":
            ipv6_color, comment, comment_color = "32", "Full IPv6 connectivity available", "32"
        elif ipv6_scope == "unique-local":
            ipv6_color, comment, comment_color = "36", "Internal (VPN/local) IPv6 — not Internet-routable", "36"
        elif ipv6_scope == "link-local":
            ipv6_color = "33"
            comment = "Link-local only — IPv6 not usable beyond local segment" + (
                " (fallback to IPv4 likely)" if ipv4 else "")
            comment_color = "33"
        elif ipv6_scope == "loopback":
            ipv6_color, comment, comment_color = "34", "Loopback address — internal-only interface", "34"
        elif ipv6_scope == "none":
            ipv6_color = "31"
            comment = "IPv6 not active on this interface" if ipv4 else "Interface offline or unconfigured"
            comment_color = "36" if ipv4 else "31"
        else:
            ipv6_color, comment, comment_color = "36", "Unknown or ambiguous IPv6 state", "33"

        ipv6_display = f"IPv6: {ipv6}" if ipv6 else "IPv6: NONE"
        ipv6_str = CLIOutputManager.color(f"| {ipv6_display.ljust(39)} |", ipv6_color)
        role_comment = CLIOutputManager.color(f"[{describe_interface(interface, ipv6_scope)}]", "90")
        comment_str = CLIOutputManager.color(comment, comment_color)

        print(f"INTERFACE: {interface.ljust(12)}  {ipv4_str}  {ipv6_str}  {comment_str} {role_comment}")

    @staticmethod
    def print_resolver_status(resolver):
        interface = resolver.interface.ljust(15)
        address = resolver.ip
        source_type = resolver.source
        provider = nameserver_to_provider(address).ljust(20)
        provider_str = CLIOutputManager.color(f"| {provider} |", "32" if "Unknown" not in provider else "31")
        address_str = CLIOutputManager.color(f"| Address: {address.ljust(30)} |", "32")
        activity_str = CLIOutputManager.color("|  Active  |", "32") if resolver.isActive else (
                        CLIOutputManager.color("| Inactive |", "31"))


        def type_col(label: str, color_code: str) -> str:
            padded = f"| {label.center(24)} |"
            return CLIOutputManager.color(padded, color_code)

        if source_type == "Custom":
            type_str = type_col("Custom", "32")
        elif source_type == "VPN Tunnel Provided":
            type_str = type_col("VPN Provided", "36")
        elif source_type == "Likely DHCP provisioned":
            type_str = type_col("DHCP", "31")
        elif source_type == "VPN Intercepted":
            address_str = CLIOutputManager.color(f"| Address: {address.ljust(30)} |", "31")
            type_str = type_col("VPN Intercepted", "33")
        else:
            type_str = type_col(source_type, "90")

        print(f"INTERFACE: {interface}  {address_str}  {type_str}  {provider_str} {activity_str}")
    @staticmethod
    def banner_phase(title: str, subtitle: str):
        print(CLIOutputManager.color(f"""
    ╔════════════════════════════════════════════════════╗
    ║{title.center(52)}║
    ║{subtitle.center(52)}║
    ╚════════════════════════════════════════════════════╝
""", "36"))

    @staticmethod
    def print_phase_1():
        CLIOutputManager.banner_phase("PHASE 1", "Check YOUR SYSTEM compatibility")

    @staticmethod
    def print_phase_2():
        CLIOutputManager.banner_phase("PHASE 2", "Check Local (DHCP) DNS Settings")

    @staticmethod
    def print_phase_3():
        CLIOutputManager.banner_phase("PHASE 3", "Check Public DNS Reachability")

    @staticmethod
    def print_phase_4():
        CLIOutputManager.banner_phase("PHASE 4", "Check Real IPv6 Website Access")

    @staticmethod
    def print_phase_5():
        CLIOutputManager.banner_phase("PHASE 5", "Report and Attempt Fix")
