class CLIOutputManager:
    @staticmethod
    def show_interface_down_warning():
        print("""\033[33m
  +------------------------------------------------------------+
  |                            .                               |
  |                           / \\                              |
  |                          / | \\                             |
  |                         /  |  \\                            |
  |                        /   o   \\                           |
  |                       -----------                          |
  |  WARNING: NO DNSv6 SERVERS ON THIS INTERFACE               |
  |                                                            |
  |  Please check your IPv6 configuration and DNS setup        |
  |  to ensure IPv6 connectivity and DNS resolution.           |
  +------------------------------------------------------------+
\033[0m
""")

    @staticmethod
    def show_all_interfaces_failure():
        print("""\033[31m
  +------------------------------------------------------------+
  |                                                            |
  |                         \\  /                               |
  |                          \\/                                |
  |                          /\\                                |
  |                         /  \\                               |
  |                                                            |
  |  ERROR: NO DNSv6 SERVERS REACHABLE ON ANY ACTIVE INTERFACE |
  |                                                            |
  |  Please ensure your network configuration supports IPv6    |
  |  and that DNS servers are correctly configured.            |
  +------------------------------------------------------------+
\033[0m
""")

    @staticmethod
    def show_all_interfaces_success(ifaces):
        print("""\033[32m
  +------------------------------------------------------------+
  |                                                            |
  |                 +---+      +   +                           |
  |                 |   |      |   |                           |
  |                 |   |      |  /                            |
  |                 |   |      |  \\                            |
  |                 |   |      |   |                           |
  |                 +---+      +   +                           |
  |                                                            |
  |  SUCCESS: DNSv6 SERVERS REACHABLE ON THESE INTERFACES      |
  +------------------------------------------------------------+
\033[0m""")
        for iface in ifaces:
            print(f"- {iface}")
        print("\033[0m")

    @staticmethod
    def prompt_ipv6_enable():
        print("\033[32m Should we attempt enabling IPv6 on IPv4 interfaces? (y/N)\033[0m")

    @staticmethod
    def print_ipv4_success():
        print("\033[32m Some DNS servers reachable via IPv4 on this interface.\033[0m")

    @staticmethod
    def print_ipv6_success():
        print("\033[32m Some DNS servers reachable via IPv6 on this interface.\033[0m")

    @staticmethod
    def print_ipv4_missing():
        print("\033[31mNo DNS servers reachable via IPv4 on any active interface.\033[0m")
        print("\033[31mYou are likely offline.\033[0m")

    @staticmethod
    def print_ipv6_attempting_enable():
        print("\033[32m Attempting to enable IPv6 on IPv4 interfaces...\033[0m")

    @staticmethod
    def print_ipv6_skipped():
        print("\033[31m Skipping IPv6 enabling on IPv4 interfaces.\033[0m")
        print("\033[31m Please check your network configuration manually.\033[0m")

    @staticmethod
    def print_ipv6_enable_failed_message():
        print("\033[31m Since enabling IPv6 did not help, "
              "your network likely does not currently support IPv6. "
              "Please contact your network administrator to enable it.\033[0m")

    def print_interface_status(interface: str, ipv4: str = None, ipv6: str = None):
        def color(text, code):
            return f"\033[{code}m{text}\033[0m"

        def classify_ipv6(ip: str) -> str:
            if not ip:
                return "none"
            if ip == "::1":
                return "loopback"
            if ip.startswith("fe80"):
                return "link-local"
            if ip.startswith("2") or ip.startswith("3"):
                return "global"
            return "other"

        # IPv4 formatting
        ipv4_display = f"IPv4: {ipv4}" if ipv4 else "IPv4: NONE"
        ipv4_color_code = "32" if ipv4 else "31"
        ipv4_str = color(f"| {ipv4_display.ljust(18)} |", ipv4_color_code)

        # IPv6 classification and formatting
        ipv6_scope = classify_ipv6(ipv6)
        if ipv6_scope == "global":
            ipv6_color = "32"
            comment = "This interface is fully IPv6-capable"
            comment_color = "32"
        elif ipv6_scope == "link-local":
            ipv6_color = "33"
            comment = (
                "This interface supports IPv6, but your network doesn't offer global access"
                if ipv4 else
                "This interface is likely offline or only for local connectivity"
            )
            comment_color = "33" if ipv4 else "31"
        elif ipv6_scope == "none":
            ipv6_color = "31"
            comment = (
                "This interface does not support IPv6 - but we can try enabling it"
                if ipv4 else
                "This interface is offline"
            )
            comment_color = "36" if ipv4 else "31"
        else:
            ipv6_color = "36"
            comment = "Unknown or mixed state"
            comment_color = "33"

        ipv6_display = f"IPv6: {ipv6}" if ipv6 else "IPv6: NONE"
        ipv6_str = color(f"| {ipv6_display.ljust(39)} |", ipv6_color)

        comment_str = color(comment, comment_color)

        # Output with alignment
        print(
            f"INTERFACE: {interface.ljust(12)}  {ipv4_str}  {ipv6_str}  {comment_str}"
        )


    @staticmethod
    def print_phase_1():
        print("\033[34m Phase 1: Checking DNS connectivity on active interfaces...\033[0m")

    @staticmethod
    def banner_phase_1():
        print("""\033[36m
    ╔════════════════════════════════════════════════════╗
    ║                     PHASE 1                        ║
    ║             Check YOUR SYSTEM compatibility        ║
    ╚════════════════════════════════════════════════════╝
    \033[0m""")

    @staticmethod
    def banner_phase_2():
        print("""\033[36m
    ╔════════════════════════════════════════════════════╗
    ║                     PHASE 2                        ║
    ║             Check Local (DHCP) DNS Settings        ║
    ╚════════════════════════════════════════════════════╝
    \033[0m""")

    @staticmethod
    def banner_phase_3():
        print("""\033[36m
    ╔════════════════════════════════════════════════════╗
    ║                     PHASE 3                        ║
    ║              Check Public DNS Reachability         ║
    ╚════════════════════════════════════════════════════╝
    \033[0m""")

    @staticmethod
    def banner_phase_4():
        print("""\033[36m
    ╔════════════════════════════════════════════════════╗
    ║                     PHASE 4                        ║
    ║             Check Real IPv6 Website Access         ║
    ╚════════════════════════════════════════════════════╝
    \033[0m""")

    @staticmethod
    def banner_phase_5():
        print("""\033[36m
    ╔════════════════════════════════════════════════════╗
    ║                     PHASE 5                        ║
    ║                Report and Attempt Fix              ║
    ╚════════════════════════════════════════════════════╝
    \033[0m""")

