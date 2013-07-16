iptables -F

# Default policy is drop
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

iptables -A INPUT -p tcp -m multiport --dports 22 -j fail2ban-ssh
iptables -A fail2ban-ssh -j RETURN

# Allow localhost
iptables -A INPUT  -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Allow incoming SSH
iptables -A INPUT  -p tcp --dport 22 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A OUTPUT -p tcp --sport 22 -m state --state ESTABLISHED -j ACCEPT

# Allow outgoing SSH
iptables -A OUTPUT -p tcp --dport 22 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A INPUT  -p tcp --sport 22 -m state --state ESTABLISHED -j ACCEPT

# Allow incoming HTTP/S
iptables -A INPUT  -p tcp --dport 80  -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A OUTPUT -p tcp --sport 80  -m state --state ESTABLISHED -j ACCEPT
iptables -A INPUT  -p tcp --dport 443 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A OUTPUT -p tcp --sport 443 -m state --state ESTABLISHED -j ACCEPT

# Allow outgoing HTTP(s)
iptables -A INPUT  -p tcp --sport 80 -m state --state ESTABLISHED -j ACCEPT
iptables -A OUTPUT -p tcp --dport 80 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A INPUT  -p tcp --sport 443 -m state --state ESTABLISHED -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -m state --state NEW,ESTABLISHED -j ACCEPT

# Allow outbound DHCP (a linode thang)
iptables -A OUTPUT -p udp --dport 67:68 -j ACCEPT
iptables -A INPUT  -p udp --sport 67:68 -j ACCEPT

# Allow outbound DNS
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A INPUT  -p udp --sport 53 -j ACCEPT

# Allow inbound munin-node
iptables -A INPUT  -p tcp --dport 4949 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A OUTPUT -p tcp --sport 4949 -m state --state ESTABLISHED -j ACCEPT

# Allow outbound git 9418/tcp
iptables -A OUTPUT -p tcp --dport 9418 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A INPUT  -p tcp --sport 9418 -m state --state ESTABLISHED -j ACCEPT

# Allow outbound xmpp 5222/tcp
iptables -A OUTPUT -p tcp --dport 5222 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A INPUT  -p tcp --sport 5222 -m state --state ESTABLISHED -j ACCEPT
