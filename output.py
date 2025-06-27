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